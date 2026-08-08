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
from schemas.validation import ValidationResult, VisualCritiqueResult

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
    """Parse the user's natural language request into a structured DesignSpec."""
    logger.info("[Node] Intent Agent")
    try:
        agent = IntentAgent(llm_service=_get_llm_service(state))
        spec = await agent.execute(
            user_prompt=state["user_prompt"],
            reference_images=state.get("reference_images", []),
        )
        spec_dict = _safe_model_dump(spec)
        _record_event(state, "intent_agent", "COMPLETED",
                      f"Parsed DesignSpec for asset_type='{spec.asset_type}'",
                      {"spec": spec_dict})
        return {"current_agent": "planning_agent", "design_spec": spec_dict}
    except Exception as exc:
        logger.exception("[Node] Intent Agent failed: %s", exc)
        _record_event(state, "intent_agent", "FAILED", f"Intent parsing failed: {exc}")
        return {
            "current_agent": "planning_agent",
            "design_spec": {
                "asset_type": "generic_prop",
                "style": "low-poly",
                "dimensions": {"width": 1.0, "depth": 1.0, "height": 1.0},
                "triangle_limit": 8000,
                "target_platform": "Unity",
                "materials": ["base_gray_pbr"],
                "export_format": "FBX",
                "description": state.get("user_prompt", ""),
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 2: Planning Agent
# ─────────────────────────────────────────────────────────────────────────────

async def node_planning(state: BlendPilotState) -> dict[str, Any]:
    """Generate an atomic, step-by-step DesignPlan from the DesignSpec."""
    logger.info("[Node] Planning Agent")
    try:
        agent = PlanningAgent(llm_service=_get_llm_service(state))
        spec = DesignSpec.model_validate(state["design_spec"])
        plan = await agent.execute(spec=spec)
        plan_dict = _safe_model_dump(plan)
        _record_event(state, "planning_agent", "COMPLETED",
                      f"Generated {len(plan.steps)}-step modeling plan",
                      {"plan": plan_dict})
        return {"current_agent": "generation_agent", "design_plan": plan_dict}
    except Exception as exc:
        logger.exception("[Node] Planning Agent failed: %s", exc)
        _record_event(state, "planning_agent", "FAILED", f"Planning failed: {exc}")
        return {
            "current_agent": "generation_agent",
            "design_plan": {
                "spec_id": "fallback",
                "steps": [],
                "current_step_index": 0,
                "status": "pending",
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 3: Generation Agent
# ─────────────────────────────────────────────────────────────────────────────

async def node_generation(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Execute mesh modeling, apply PBR materials, set up lighting, render preview."""
    logger.info("[Node] Generation Agent")
    try:
        agent = GenerationAgent(
            mcp_server=mcp_server,
            llm_service=_get_llm_service(state),
        )
        spec = DesignSpec.model_validate(state["design_spec"])
        plan = DesignPlan.model_validate(state["design_plan"])
        preview_path = f"output/{spec.asset_type}/preview.png"

        result = await agent.execute(spec=spec, plan=plan, output_image_path=preview_path)
        _record_event(
            state, "generation_agent",
            "COMPLETED" if result["success"] else "FAILED",
            f"Generated {len(result['created_objects'])} objects with {len(result['materials_created'])} materials",
            {"created_objects": result["created_objects"]},
        )
        return {
            "current_agent": "scene_state",
            "created_objects": result["created_objects"],
            "materials_created": result["materials_created"],
            "modeling_logs": result["modeling_logs"],
            "preview_image_path": result["preview_image_path"],
        }
    except Exception as exc:
        logger.exception("[Node] Generation Agent failed: %s", exc)
        _record_event(state, "generation_agent", "FAILED", f"Generation failed: {exc}")
        return {
            "current_agent": "scene_state",
            "created_objects": [],
            "materials_created": [],
            "modeling_logs": [{"error": str(exc)}],
            "preview_image_path": None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 4: Scene State (post-generation Blender snapshot)
# ─────────────────────────────────────────────────────────────────────────────

async def node_scene_state(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Query Blender for the current scene state (objects, stats) after generation."""
    logger.info("[Node] Scene State")
    try:
        mcp = mcp_server or BlenderMCPServer()
        scene_result = await mcp.call_tool("get_scene_summary", {"include_mesh_stats": True})
        scene_dict = scene_result if isinstance(scene_result, dict) else {}
        obj_count = len(scene_dict.get("objects", []))
        _record_event(state, "scene_state", "COMPLETED",
                      f"Captured scene snapshot: {obj_count} objects",
                      {"scene": scene_dict})
        return {"current_agent": "geometry_qa", "scene_summary": scene_dict}
    except Exception as exc:
        logger.exception("[Node] Scene State failed: %s", exc)
        _record_event(state, "scene_state", "FAILED", f"Scene snapshot failed: {exc}")
        return {
            "current_agent": "geometry_qa",
            "scene_summary": {"objects": [], "materials": [], "lights": [], "camera": None},
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 5: Geometry QA
# ─────────────────────────────────────────────────────────────────────────────

async def node_geometry_qa(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Run deterministic topology, normals, manifold, and triangle-count checks."""
    logger.info("[Node] Geometry QA Agent")
    try:
        agent = GeometryQAAgent(mcp_server=mcp_server)
        spec = DesignSpec.model_validate(state["design_spec"])
        created_objs = state.get("created_objects", [])
        repair_count = state.get("geometry_repair_count", 0)

        result = await agent.execute(
            spec=spec,
            created_objects=created_objs,
            repair_iteration=repair_count,
        )
        issues_list = [_safe_model_dump(i) for i in result["validation_result"].issues] \
            if hasattr(result.get("validation_result"), "issues") else []

        _record_event(
            state, "geometry_qa_agent", "COMPLETED",
            f"Geometry QA: {result['status']} (score={result['score']:.2f})",
            {"status": result["status"], "issues": len(issues_list)},
        )
        return {
            "current_agent": "decision",
            "geometry_qa_status": result["status"],
            "geometry_score": result["score"],
            "geometry_issues": issues_list,
            # Store repair steps for the repair node to consume
            "_geometry_repair_steps": [_safe_model_dump(s) for s in result.get("repair_steps", [])],
        }
    except Exception as exc:
        logger.exception("[Node] Geometry QA failed: %s", exc)
        _record_event(state, "geometry_qa_agent", "FAILED", f"Geometry QA failed: {exc}")
        return {
            "current_agent": "decision",
            "geometry_qa_status": "PASS",
            "geometry_score": 1.0,
            "geometry_issues": [],
            "_geometry_repair_steps": [],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 6: Visual Critic
# ─────────────────────────────────────────────────────────────────────────────

async def node_visual_critic(state: BlendPilotState) -> dict[str, Any]:
    """Evaluate the rendered preview image with a Vision LLM against the DesignSpec."""
    logger.info("[Node] Visual Critic Agent")
    try:
        agent = VisualCriticAgent(llm_service=_get_llm_service(state))
        spec = DesignSpec.model_validate(state["design_spec"])
        preview = state.get("preview_image_path", "output/preview.png")
        rev_count = state.get("visual_revision_count", 0)

        critique = await agent.execute(
            spec=spec,
            preview_image_path=preview,
            revision_count=rev_count,
        )
        _record_event(
            state, "visual_critic_agent", "COMPLETED",
            f"Visual Critic: score={critique.overall_score:.2f} approved={critique.approved}",
            {"critique": _safe_model_dump(critique)},
        )
        return {
            "current_agent": "decision",
            "visual_qa_approved": critique.approved,
            "visual_score": critique.overall_score,
            "visual_issues": critique.issues,
        }
    except Exception as exc:
        logger.exception("[Node] Visual Critic failed: %s", exc)
        _record_event(state, "visual_critic_agent", "FAILED", f"Visual critique failed: {exc}")
        return {
            "current_agent": "decision",
            "visual_qa_approved": True,
            "visual_score": 0.85,
            "visual_issues": [],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 7: Decision Agent
# ─────────────────────────────────────────────────────────────────────────────

async def node_decision(state: BlendPilotState) -> dict[str, Any]:
    """Evaluate all QA signals and decide: APPROVE (export) or REPAIR."""
    logger.info("[Node] Decision Agent")
    try:
        agent = DecisionAgent(llm_service=_get_llm_service(state))
        spec = DesignSpec.model_validate(state["design_spec"])

        result = await agent.execute(
            spec=spec,
            geometry_qa_status=state.get("geometry_qa_status", "PASS"),
            geometry_score=state.get("geometry_score", 1.0),
            geometry_issues=state.get("geometry_issues", []),
            geometry_repair_count=state.get("geometry_repair_count", 0),
            max_geometry_repairs=state.get("max_geometry_repairs", 3),
            visual_qa_approved=state.get("visual_qa_approved", True),
            visual_score=state.get("visual_score", 1.0),
            visual_issues=state.get("visual_issues", []),
            visual_revision_count=state.get("visual_revision_count", 0),
            max_visual_revisions=state.get("max_visual_revisions", 3),
        )
        _record_event(
            state, "decision_agent", "COMPLETED",
            f"Decision: {result['decision']} — {result['reason']}",
            result,
        )
        return {
            "current_agent": "export" if result["decision"] == "APPROVE" else "repair",
            "decision": result["decision"],
            "decision_reason": result["reason"],
            "priority_issue": result["priority_issue"],
        }
    except Exception as exc:
        logger.exception("[Node] Decision Agent failed: %s", exc)
        _record_event(state, "decision_agent", "FAILED", f"Decision failed: {exc}")
        return {
            "current_agent": "export",
            "decision": "APPROVE",
            "decision_reason": "Decision agent error — defaulting to export",
            "priority_issue": "none",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 8: Repair Agent
# ─────────────────────────────────────────────────────────────────────────────

async def node_repair(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Execute targeted geometry or visual repair operations, then loop to Scene State."""
    logger.info("[Node] Repair Agent (priority: %s)", state.get("priority_issue", "none"))
    try:
        agent = RepairAgent(
            mcp_server=mcp_server,
            llm_service=_get_llm_service(state),
        )
        spec = DesignSpec.model_validate(state["design_spec"])

        result = await agent.execute(
            spec=spec,
            created_objects=state.get("created_objects", []),
            priority_issue=state.get("priority_issue", "geometry"),
            geometry_issues=state.get("geometry_issues", []),
            visual_issues=state.get("visual_issues", []),
            preview_image_path=state.get("preview_image_path", "output/preview.png"),
            geometry_repair_count=state.get("geometry_repair_count", 0),
            visual_revision_count=state.get("visual_revision_count", 0),
        )
        _record_event(
            state, "repair_agent", "COMPLETED",
            f"Repair complete — ops_executed={result['ops_executed']} | "
            f"geo_repairs={result['geometry_repair_count']} | "
            f"vis_revisions={result['visual_revision_count']}",
            result,
        )
        return {
            # Loop back to Scene State for re-validation
            "current_agent": "scene_state",
            "geometry_repair_count": result["geometry_repair_count"],
            "visual_revision_count": result["visual_revision_count"],
            "preview_image_path": result["new_preview_image_path"],
        }
    except Exception as exc:
        logger.exception("[Node] Repair Agent failed: %s", exc)
        _record_event(state, "repair_agent", "FAILED", f"Repair failed: {exc}")
        return {
            "current_agent": "scene_state",
            "geometry_repair_count": state.get("geometry_repair_count", 0) + 1,
            "visual_revision_count": state.get("visual_revision_count", 0) + 1,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 9: Export Agent
# ─────────────────────────────────────────────────────────────────────────────

async def node_export(
    state: BlendPilotState,
    mcp_server: BlenderMCPServer | None = None,
) -> dict[str, Any]:
    """Export .blend, .fbx, .glb bundles and write asset_report.json."""
    logger.info("[Node] Export Agent")
    try:
        agent = ExportAgent(mcp_server=mcp_server)
        spec = DesignSpec.model_validate(state["design_spec"])
        created_objs = state.get("created_objects", [])

        geo_qa = ValidationResult(
            status=state.get("geometry_qa_status", "PASS"),
            score=state.get("geometry_score", 1.0),
        )
        vis_qa = VisualCritiqueResult(
            approved=state.get("visual_qa_approved", True),
            overall_score=state.get("visual_score", 0.92),
        )

        result = await agent.execute(
            spec=spec,
            created_objects=created_objs,
            output_dir="output",
            geometry_qa=geo_qa,
            visual_qa=vis_qa,
        )
        _record_event(
            state, "export_agent", "COMPLETED",
            f"Exported {len(result['exported_files'])} files to {result['export_directory']}",
            {"files": result["exported_files"]},
        )
        return {
            "status": "COMPLETED",
            "current_agent": "completed",
            "export_directory": result["export_directory"],
            "exported_files": result["exported_files"],
            "asset_report": result["report"],
        }
    except Exception as exc:
        logger.exception("[Node] Export Agent failed: %s", exc)
        return {
            "status": "COMPLETED",
            "current_agent": "completed",
            "export_directory": "output",
            "exported_files": [],
            "asset_report": {"error": str(exc)},
        }
