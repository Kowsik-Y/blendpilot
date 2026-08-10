"""
BlendPilot AI — LangGraph Node Implementations

Implements the target architecture pipeline:
    Intent → Planning → Generation → Scene State →
    Geometry QA → Visual Critic → Decision → Repair → Re-validation → Export

Each node function:
  - Receives the full BlendPilotState
  - Returns a plain dict of state updates (never tuples or non-dict types)
  - Logs a structured AgentStepEvent for SSE streaming
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from agents.decision_agent import DecisionAgent
from agents.export_agent import ExportAgent
from agents.generation_agent import GenerationAgent
from agents.geometry_qa_agent import GeometryQAAgent
from agents.intent_agent import IntentAgent
from agents.planning_agent import PlanningAgent
from agents.repair_agent import RepairAgent
from agents.visual_critic_agent import VisualCriticAgent
from graph.state import BlendPilotState
from mcp_servers.blender.server import BlenderMCPServer
from schemas.design import DesignSpec
from schemas.plan import DesignPlan

logger = logging.getLogger("blendpilot.graph.nodes")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _record_event(
    state: BlendPilotState,
    agent_name: str,
    status: str,
    description: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Append a structured step event to the state log."""
    events = state.get("events", [])
    events.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_name": agent_name,
        "status": status,
        "step_description": description,
        "details": details or {},
    })
    state["events"] = events


def _get_llm_service(state: BlendPilotState) -> Any:
    """Instantiate LLMService with any user-provided API key from state."""
    from services.llm import LLMService
    return LLMService(
        api_key=state.get("api_key"),
        provider=state.get("provider") or "openai",
    )


def _safe_model_dump(obj: Any) -> Any:
    """Safely convert a Pydantic model or dict to a plain dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    return str(obj)


# ─────────────────────────────────────────────────────────────────────────────
# Node 1: Intent Agent
# ─────────────────────────────────────────────────────────────────────────────

async def node_intent(state: BlendPilotState) -> dict[str, Any]:
    """Parse the user's natural language request into a structured DesignSpec / IntentSpec."""
    logger.info("[Node] Intent Agent")
    try:
        agent = IntentAgent(llm_service=_get_llm_service(state))
        spec = await agent.execute(
            user_prompt=state["user_prompt"],
            reference_images=state.get("reference_images", []),
        )
        spec_dict = _safe_model_dump(spec)
        asset_type = getattr(spec, 'asset_type', getattr(spec, 'object_type', 'unknown'))
        _record_event(state, "intent_agent", "COMPLETED",
                      f"Parsed IntentSpec for object_type='{asset_type}'",
                      {"spec": spec_dict})
        return {
            "current_agent": "planner",
            "intent": spec_dict,
            "design_spec": spec_dict
        }
    except Exception as exc:
        logger.exception("[Node] Intent Agent failed: %s", exc)
        _record_event(state, "intent_agent", "FAILED", f"Intent parsing failed: {exc}")
        return {
            "current_agent": "planner",
            "intent": {
                "object_type": "generic_prop",
                "style": "low-poly",
                "dimensions": {"width": 1.0, "depth": 1.0, "height": 1.0},
                "materials": ["base_gray_pbr"],
                "description": state.get("user_prompt", ""),
            },
            "design_spec": {
                "asset_type": "generic_prop",
                "style": "low-poly",
                "dimensions": {"width": 1.0, "depth": 1.0, "height": 1.0},
                "materials": ["base_gray_pbr"],
                "description": state.get("user_prompt", ""),
            },
            "errors": state.get("errors", []) + [str(exc)]
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 2: Planner Agent
# ─────────────────────────────────────────────────────────────────────────────

async def node_planner(state: BlendPilotState) -> dict[str, Any]:
    """Generate modeling plan from intent spec."""
    logger.info("[Node] Planner Agent")
    try:
        agent = PlanningAgent(llm_service=_get_llm_service(state))
        spec_dict = state.get("intent") or state.get("design_spec")
        from schemas.intent import IntentSpec
        spec = IntentSpec.model_validate(spec_dict)
        plan = await agent.execute(intent=spec)
        plan_dict = _safe_model_dump(plan)
        _record_event(state, "planning_agent", "COMPLETED",
                      f"Generated {len(plan.steps)}-step modeling plan",
                      {"plan": plan_dict})
        return {
            "current_agent": "generator",
            "plan": plan_dict,
            "design_plan": plan_dict
        }
    except Exception as exc:
        logger.exception("[Node] Planner Agent failed: %s", exc)
        _record_event(state, "planning_agent", "FAILED", f"Planning failed: {exc}")
        return {
            "current_agent": "generator",
            "plan": {"steps": []},
            "design_plan": {"steps": []},
            "errors": state.get("errors", []) + [str(exc)],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 3: Generator Agent
# ─────────────────────────────────────────────────────────────────────────────

async def node_generator(state: BlendPilotState) -> dict[str, Any]:
    """Translate ModelingPlan into list of executable operations."""
    logger.info("[Node] Generator Agent")
    try:
        agent = GenerationAgent(llm_service=_get_llm_service(state))
        plan_dict = state.get("plan") or state.get("design_plan")
        from schemas.plan_state import ModelingPlan
        plan = ModelingPlan.model_validate(plan_dict)
        
        ops = agent.translate(plan)
        _record_event(state, "generation_agent", "COMPLETED",
                      f"Translated modeling plan to {len(ops)} executable operations",
                      {"operations": ops})
        return {
            "current_agent": "executor",
            "executable_operations": ops,
        }
    except Exception as exc:
        logger.exception("[Node] Generator Agent failed: %s", exc)
        _record_event(state, "generation_agent", "FAILED", f"Translation failed: {exc}")
        return {
            "current_agent": "executor",
            "executable_operations": [],
            "errors": state.get("errors", []) + [str(exc)],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 4: Executor Agent
# ─────────────────────────────────────────────────────────────────────────────

async def node_executor(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Execute the list of operations in the Blender context."""
    logger.info("[Node] Executor Agent")
    try:
        try:
            import bpy
            mock_mode = False
        except ImportError:
            mock_mode = True

        agent = GenerationAgent(
            mcp_server=mcp_server,
            llm_service=_get_llm_service(state),
            mock_mode=mock_mode,
        )
        
        spec_dict = state.get("intent") or state.get("design_spec")
        plan_dict = state.get("plan") or state.get("design_plan")
        from schemas.intent import IntentSpec
        from schemas.plan_state import ModelingPlan
        spec = IntentSpec.model_validate(spec_dict)
        plan = ModelingPlan.model_validate(plan_dict)
        
        preview_path = f"output/{spec.object_type}/preview.png"
        result = await agent.execute(spec=spec, plan=plan, output_image_path=preview_path)
        
        status = "COMPLETED" if result["success"] else "FAILED"
        _record_event(
            state, "executor_agent",
            status,
            f"Executed {len(plan.steps)} operations: {len(result['created_objects'])} objects, {len(result['materials_created'])} materials",
            {"created_objects": result["created_objects"]},
        )
        
        return {
            "current_agent": "scene_state_node",
            "created_objects": result["created_objects"],
            "materials_created": result["materials_created"],
            "modeling_logs": _safe_model_dump(result["step_executions"]),
            "preview_image_path": result["preview_image_path"],
            "execution_result": result,
            "status": status,
            "errors": state.get("errors", []) + ([] if result["success"] else ["Some operations failed to execute"]),
            "iteration_count": state.get("iteration_count", 0) + 1,
        }
    except Exception as exc:
        logger.exception("[Node] Executor Agent failed: %s", exc)
        _record_event(state, "executor_agent", "FAILED", f"Execution failed: {exc}")
        return {
            "current_agent": "scene_state_node",
            "created_objects": [],
            "materials_created": [],
            "modeling_logs": [{"error": str(exc)}],
            "preview_image_path": None,
            "execution_result": {"success": False, "step_executions": []},
            "status": "FAILED",
            "errors": state.get("errors", []) + [str(exc)],
            "iteration_count": state.get("iteration_count", 0) + 1,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 5: Scene State (post-generation Blender snapshot)
# ─────────────────────────────────────────────────────────────────────────────

async def node_scene_state(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Query Blender for the current scene state (objects, stats) after generation."""
    logger.info("[Node] Scene State")
    try:
        from core.scene_inspector import inspect_scene
        scene_summary = inspect_scene()
        scene_dict = _safe_model_dump(scene_summary)
        obj_count = len(scene_summary.objects)
        _record_event(state, "scene_state", "COMPLETED",
                      f"Captured scene snapshot: {obj_count} objects",
                      {"scene": scene_dict})
        return {
            "current_agent": "geometry_qa",
            "scene_summary": scene_dict,
            "scene_state": scene_dict,
            "status": "COMPLETED",
        }
    except Exception as exc:
        logger.exception("[Node] Scene State failed: %s", exc)
        _record_event(state, "scene_state", "FAILED", f"Scene snapshot failed: {exc}")
        return {
            "current_agent": "END",
            "scene_summary": {"objects": [], "materials": [], "lighting": [], "camera": None},
            "scene_state": {"objects": [], "materials": [], "lighting": [], "camera": None},
            "status": "FAILED",
            "errors": state.get("errors", []) + [str(exc)],
        }

        return {
            "current_agent": "planner",
            "intent": spec_dict,
            "design_spec": spec_dict
        }
    except Exception as exc:
        logger.exception("[Node] Intent Agent failed: %s", exc)
        _record_event(state, "intent_agent", "FAILED", f"Intent parsing failed: {exc}")
        return {
            "current_agent": "planner",
            "intent": {
                "object_type": "generic_prop",
                "style": "low-poly",
                "dimensions": {"width": 1.0, "depth": 1.0, "height": 1.0},
                "materials": ["base_gray_pbr"],
                "description": state.get("user_prompt", ""),
            },
            "design_spec": {
                "asset_type": "generic_prop",
                "style": "low-poly",
                "dimensions": {"width": 1.0, "depth": 1.0, "height": 1.0},
                "materials": ["base_gray_pbr"],
                "description": state.get("user_prompt", ""),
            },
            "errors": state.get("errors", []) + [str(exc)]
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 2: Planner Agent
# ─────────────────────────────────────────────────────────────────────────────

async def node_planner(state: BlendPilotState) -> dict[str, Any]:
    """Generate modeling plan from intent spec."""
    logger.info("[Node] Planner Agent")
    try:
        agent = PlanningAgent(llm_service=_get_llm_service(state))
        spec_dict = state.get("intent") or state.get("design_spec")
        from schemas.intent import IntentSpec
        spec = IntentSpec.model_validate(spec_dict)
        plan = await agent.execute(intent=spec)
        plan_dict = _safe_model_dump(plan)
        _record_event(state, "planning_agent", "COMPLETED",
                      f"Generated {len(plan.steps)}-step modeling plan",
                      {"plan": plan_dict})
        return {
            "current_agent": "generator",
            "plan": plan_dict,
            "design_plan": plan_dict
        }
    except Exception as exc:
        logger.exception("[Node] Planner Agent failed: %s", exc)
        _record_event(state, "planning_agent", "FAILED", f"Planning failed: {exc}")
        return {
            "current_agent": "generator",
            "plan": {"steps": []},
            "design_plan": {"steps": []},
            "errors": state.get("errors", []) + [str(exc)],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 3: Generator Agent
# ─────────────────────────────────────────────────────────────────────────────

async def node_generator(state: BlendPilotState) -> dict[str, Any]:
    """Translate ModelingPlan into list of executable operations."""
    logger.info("[Node] Generator Agent")
    try:
        agent = GenerationAgent(llm_service=_get_llm_service(state))
        plan_dict = state.get("plan") or state.get("design_plan")
        from schemas.plan_state import ModelingPlan
        plan = ModelingPlan.model_validate(plan_dict)
        
        ops = agent.translate(plan)
        _record_event(state, "generation_agent", "COMPLETED",
                      f"Translated modeling plan to {len(ops)} executable operations",
                      {"operations": ops})
        return {
            "current_agent": "executor",
            "executable_operations": ops,
        }
    except Exception as exc:
        logger.exception("[Node] Generator Agent failed: %s", exc)
        _record_event(state, "generation_agent", "FAILED", f"Translation failed: {exc}")
        return {
            "current_agent": "executor",
            "executable_operations": [],
            "errors": state.get("errors", []) + [str(exc)],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 4: Executor Agent
# ─────────────────────────────────────────────────────────────────────────────

async def node_executor(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Execute the list of operations in the Blender context."""
    logger.info("[Node] Executor Agent")
    try:
        mock_mode = state.get("baseline_mode", False)

        agent = GenerationAgent(
            mcp_server=mcp_server,
            llm_service=_get_llm_service(state),
            mock_mode=mock_mode,
        )
        
        spec_dict = state.get("intent") or state.get("design_spec")
        plan_dict = state.get("plan") or state.get("design_plan")
        from schemas.intent import IntentSpec
        from schemas.plan_state import ModelingPlan
        spec = IntentSpec.model_validate(spec_dict)
        plan = ModelingPlan.model_validate(plan_dict)
        
        preview_path = f"output/{spec.object_type}/preview.png"
        result = await agent.execute(spec=spec, plan=plan, output_image_path=preview_path)
        
        status = "COMPLETED" if result["success"] else "FAILED"
        _record_event(
            state, "executor_agent",
            status,
            f"Executed {len(plan.steps)} operations: {len(result['created_objects'])} objects, {len(result['materials_created'])} materials",
            {"created_objects": result["created_objects"]},
        )
        
        return {
            "current_agent": "scene_state_node",
            "created_objects": result["created_objects"],
            "materials_created": result["materials_created"],
            "modeling_logs": _safe_model_dump(result["step_executions"]),
            "preview_image_path": result["preview_image_path"],
            "execution_result": result,
            # NOTE: Do NOT emit a terminal status here — the pipeline must continue
            # to SceneState → GeometryQA → VisionQA → Decision before finishing.
            "errors": state.get("errors", []) + ([] if result["success"] else ["Some operations failed to execute"]),
            "iteration_count": state.get("iteration_count", 0) + 1,
        }
    except Exception as exc:
        logger.exception("[Node] Executor Agent failed: %s", exc)
        _record_event(state, "executor_agent", "FAILED", f"Execution failed: {exc}")
        return {
            "current_agent": "scene_state_node",
            "created_objects": [],
            "materials_created": [],
            "modeling_logs": [{"error": str(exc)}],
            "preview_image_path": None,
            "execution_result": {"success": False, "step_executions": []},
            "errors": state.get("errors", []) + [str(exc)],
            "iteration_count": state.get("iteration_count", 0) + 1,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 5: Scene State (post-generation Blender snapshot)
# ─────────────────────────────────────────────────────────────────────────────

async def node_scene_state(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Query Blender for the current scene state via MCP get_scene_summary tool.

    Routes through BlenderMCPServer / BlenderClient which has a simulation
    fallback — avoids direct 'import bpy' inside the FastAPI process.
    """
    logger.info("[Node] Scene State")
    try:
        server = mcp_server or BlenderMCPServer()
        result = await server.call_tool("get_scene_summary", {})
        # call_tool returns {"success": bool, "result": {...scene data...}, "error": ...}
        # Unwrap the inner "result" key to get the actual scene dict
        if isinstance(result, dict) and "result" in result and isinstance(result["result"], dict):
            scene_dict = result["result"]
        else:
            scene_dict = result if isinstance(result, dict) else {}

        # Build a minimal scene_summary compatible with frontend schema
        objects = scene_dict.get("objects", [])
        obj_count = len(objects)

        _record_event(state, "scene_state_node", "COMPLETED",
                      f"Captured scene snapshot: {obj_count} object(s)",
                      {"object_count": obj_count})
        return {
            "current_agent": "geometry_qa",
            "scene_summary": scene_dict,
            "scene_state": scene_dict,
        }
    except Exception as exc:
        logger.exception("[Node] Scene State failed: %s", exc)
        _record_event(state, "scene_state_node", "FAILED", f"Scene snapshot failed: {exc}")
        return {
            "current_agent": "geometry_qa",
            "scene_summary": {"objects": [], "materials": [], "lighting": [], "camera": None},
            "scene_state": {"objects": [], "materials": [], "lighting": [], "camera": None},
            "errors": state.get("errors", []) + [str(exc)],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 5: Geometry QA
# ─────────────────────────────────────────────────────────────────────────────

async def node_geometry_qa(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Run deterministic geometry checks and missing object checks."""
    logger.info("[Node] Geometry QA Agent")
    try:
        agent = GeometryQAAgent(mcp_server=mcp_server)
        spec_dict = state.get("design_spec") or state.get("intent") or {}
        try:
            spec = DesignSpec.model_validate(spec_dict)
        except Exception:
            spec = DesignSpec(
                asset_type=spec_dict.get("object_type", spec_dict.get("asset_type", "generic_prop")),
                dimensions={"width": 1.0, "depth": 1.0, "height": 1.0},
                target_platform="Generic"
            )

        try:
            from schemas.plan_state import ModelingPlan
            plan = ModelingPlan.model_validate(state.get("plan") or state.get("design_plan"))
        except Exception:
            plan = ModelingPlan(steps=[])
            
        created_objs = state.get("created_objects", [])

        result = await agent.execute(
            spec=spec,
            plan=plan,
            created_objects=created_objs,
        )

        report = result.get("validation_report", {})
        passed = result.get("passed", False)

        _record_event(
            state, "geometry_qa_agent", "COMPLETED",
            f"Geometry QA: {'PASS' if passed else 'FAIL'}",
            {"report": report},
        )
        return {
            "validation_report": report,
        }
    except Exception as exc:
        logger.exception("[Node] Geometry QA failed: %s", exc)
        _record_event(state, "geometry_qa_agent", "FAILED", f"Geometry QA failed: {exc}")
        return {
            "errors": state.get("errors", []) + [str(exc)],
        }

async def node_geometry_wait(state: BlendPilotState) -> dict[str, Any]:
    """Dummy node to synchronize the Geometry QA branch with the Render -> Vision branch."""
    return {}

# ─────────────────────────────────────────────────────────────────────────────
# Node 5b: Vision Critic (Stage 11)
# ─────────────────────────────────────────────────────────────────────────────

async def node_vision_critic(state: BlendPilotState) -> dict[str, Any]:
    """Run visual critique on the rendered preview image."""
    logger.info("[Node] Vision Critic Agent")
    try:
        from agents.vision_critic_agent import VisionCriticAgent
        from schemas.design import DesignSpec
        
        agent = VisionCriticAgent(
            llm_service=_get_llm_service(state),
            mock_mode=state.get("provider") == "mock"
        )
        
        spec_dict = state.get("design_spec") or state.get("intent") or {}
        try:
            spec = DesignSpec.model_validate(spec_dict)
        except Exception:
            spec = DesignSpec(
                asset_type=spec_dict.get("object_type", spec_dict.get("asset_type", "generic_prop")),
                dimensions={"width": 1.0, "depth": 1.0, "height": 1.0},
                target_platform="Generic"
            )

        preview_path = state.get("preview_image_path", "")
        scene_summary = state.get("scene_summary", {})
        
        result = await agent.execute(
            intent=spec,
            preview_image_path=preview_path,
            scene_summary=scene_summary
        )

        report = result.get("vision_report", {})
        passed = result.get("passed", False)
        
        _record_event(
            state, "vision_critic_agent", "COMPLETED",
            f"Vision Critique: {'PASS' if passed else 'FAIL'}",
            {"report": report},
        )
        return {
            "vision_report": report,
        }
    except Exception as exc:
        logger.exception("[Node] Vision Critic failed: %s", exc)
        _record_event(state, "vision_critic_agent", "FAILED", f"Vision Critique failed: {exc}")
        return {
            "errors": state.get("errors", []) + [str(exc)],
        }

# ─────────────────────────────────────────────────────────────────────────────
# Node 5c: Render (Stage 12)
# ─────────────────────────────────────────────────────────────────────────────

async def node_render(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Render the scene preview."""
    logger.info("[Node] Render")
    try:
        from backend.config import settings
        
        spec_dict = state.get("intent") or state.get("design_spec") or {}
        obj_type = spec_dict.get("object_type", spec_dict.get("asset_type", "generic_prop"))
        preview_path = f"output/{obj_type}/preview.png"
        
        server = mcp_server or BlenderMCPServer()
        
        logger.info(f"Rendering preview to {preview_path}")
        # Note: setup_preview_camera and setup_studio_lighting should theoretically be called first,
        # but generation_agent might have done that, or render_preview does it itself if missing.
        # We'll just call render_preview directly.
        await server.call_tool("render_preview", {"output_path": preview_path})

        _record_event(state, "render", "COMPLETED", "Rendered scene preview")
        
        return {
            "preview_image_path": preview_path,
        }
    except Exception as exc:
        logger.exception("[Node] Render failed: %s", exc)
        _record_event(state, "render", "FAILED", f"Render failed: {exc}")
        return {
            "errors": state.get("errors", []) + [str(exc)],
        }

# ─────────────────────────────────────────────────────────────────────────────
# Node 5d: Decision (Stage 12)
# ─────────────────────────────────────────────────────────────────────────────

async def node_decision(state: BlendPilotState) -> dict[str, Any]:
    """Evaluate both Geometry QA and Vision QA results to route the graph."""
    logger.info("[Node] Decision Agent")
    val_report = state.get("validation_report", {})
    vis_report = state.get("vision_report", {})
    
    val_pass = val_report.get("passed", False)
    vis_pass = vis_report.get("overall_result") == "PASS"
    
    _record_event(
        state, "decision_agent", "COMPLETED",
        f"Geometry: {'PASS' if val_pass else 'FAIL'} | Vision: {'PASS' if vis_pass else 'FAIL'}"
    )
    
    return {
        "current_agent": "decision_node",
    }

# ─────────────────────────────────────────────────────────────────────────────
# Node 6: Repair Agent (Stub)
# ─────────────────────────────────────────────────────────────────────────────

async def node_repair(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Execute targeted repairs based on QA and Vision feedback."""
    logger.info("[Node] Repair Agent")
    try:
        from agents.repair_agent import RepairAgent
        
        try:
            import bpy
            mock_mode = False
        except ImportError:
            mock_mode = True

        agent = RepairAgent(
            mcp_server=mcp_server,
            llm_service=_get_llm_service(state),
            mock_mode=mock_mode,
        )

        intent = state.get("intent") or state.get("design_spec") or {}
        val_report = state.get("validation_report", {})
        vis_report = state.get("vision_report", {})
        scene_state = state.get("scene_state", {})

        result = await agent.execute(
            intent=intent,
            validation_report=val_report,
            vision_report=vis_report,
            scene_state=scene_state,
        )

        _record_event(
            state, "repair_agent", "COMPLETED",
            f"Executed {result.get('ops_executed', 0)} targeted repair operations.",
            {"repair_plan": result.get("repair_plan")}
        )

        return {
            "current_agent": "scene_state_node",
            "repair_plan": result.get("repair_plan"),
            "iteration_count": state.get("iteration_count", 0) + 1,
            "errors": state.get("errors", []) + ([] if result.get("success") else ["Some repair operations failed"]),
        }
    except Exception as exc:
        logger.exception("[Node] Repair Agent failed: %s", exc)
        _record_event(state, "repair_agent", "FAILED", f"Repair failed: {exc}")
        return {
            "current_agent": "scene_state_node",
            "errors": state.get("errors", []) + [str(exc)],
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

# ─────────────────────────────────────────────────────────────────────────────
# Node 7: Export Agent (Stub)
# ─────────────────────────────────────────────────────────────────────────────

async def node_export(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Export the finished asset using the Export Agent."""
    logger.info("[Node] Export Agent")
    try:
        server = mcp_server or BlenderMCPServer()
        
        spec_dict = state.get("intent") or state.get("design_spec") or {}
        obj_type = spec_dict.get("object_type", spec_dict.get("asset_type", "generic_prop"))
        out_dir = f"output/{obj_type}"
        
        # Save project first
        blend_path = f"{out_dir}/{obj_type}.blend"
        await server.call_tool("save_project", {"filepath": blend_path})
        
        # Export objects
        created_objects = state.get("created_objects", [])
        if created_objects:
            await server.call_tool("export_asset", {
                "object_names": created_objects,
                "output_path": f"{out_dir}/{obj_type}.glb",
                "format": "GLB"
            })
            await server.call_tool("export_asset", {
                "object_names": created_objects,
                "output_path": f"{out_dir}/{obj_type}.fbx",
                "format": "FBX"
            })
            
        _record_event(state, "export_agent", "COMPLETED", "Export completed.")
        return {"current_agent": "END", "status": "COMPLETED"}
    except Exception as exc:
        logger.exception("[Node] Export failed: %s", exc)
        _record_event(state, "export_agent", "FAILED", f"Export failed: {exc}")
        return {"current_agent": "END", "status": "COMPLETED"}

# ─────────────────────────────────────────────────────────────────────────────
# Node 8: Human Review
# ─────────────────────────────────────────────────────────────────────────────

async def node_human_review(state: BlendPilotState) -> dict[str, Any]:
    """Stops the pipeline for human review after max repair iterations."""
    logger.warning("[Node] Human Review Required (Max iterations reached)")
    _record_event(state, "human_review", "COMPLETED", "Pipeline stopped for human review.")
    return {"current_agent": "END", "status": "REVIEW_REQUIRED"}

# ─────────────────────────────────────────────────────────────────────────────
# Node 9: Refinement Agent (Stage 15)
# ─────────────────────────────────────────────────────────────────────────────

async def node_refinement(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Execute targeted natural language modifications from user."""
    logger.info("[Node] Refinement Agent")
    try:
        from agents.refinement_agent import RefinementAgent
        
        try:
            import bpy
            mock_mode = False
        except ImportError:
            mock_mode = True

        agent = RefinementAgent(
            mcp_server=mcp_server,
            llm_service=_get_llm_service(state),
            mock_mode=mock_mode,
        )

        user_prompt = state.get("user_prompt", "")
        scene_state = state.get("scene_state", {})

        result = await agent.execute(
            user_prompt=user_prompt,
            scene_state=scene_state,
        )

        _record_event(
            state, "refinement_agent", "COMPLETED",
            f"Executed {result.get('ops_executed', 0)} modification operations.",
            {"modification_plan": result.get("modification_plan")}
        )

        return {
            "current_agent": "scene_state_node",
            "repair_plan": result.get("modification_plan"),  # Reuse repair_plan key in state for logging
            "iteration_count": 0,  # Reset iteration count for new modification
            "status": "RUNNING",
            "errors": state.get("errors", []) + ([] if result.get("success") else ["Some modification operations failed"]),
        }
    except Exception as exc:
        logger.exception("[Node] Refinement Agent failed: %s", exc)
        _record_event(state, "refinement_agent", "FAILED", f"Refinement failed: {exc}")
        return {
            "current_agent": "scene_state_node",
            "errors": state.get("errors", []) + [str(exc)],
            "iteration_count": 0,
            "status": "RUNNING",
        }

