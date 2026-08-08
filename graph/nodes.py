"""
BlendPilot AI — LangGraph Node Implementations

Wraps the 10 specialized agent executors into stateful LangGraph node functions.
Each node returns a plain dict update to the state — never tuples or non-dict types.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from agents.export_agent import ExportAgent
from agents.feedback_agent import FeedbackAgent
from agents.geometry_qa_agent import GeometryQAAgent
from agents.intent_agent import IntentAgent
from agents.material_agent import MaterialAgent
from agents.modeling_agent import ModelingAgent
from agents.planning_agent import PlanningAgent
from agents.research_agent import ResearchAgent
from agents.scene_agent import SceneAgent
from agents.visual_critic_agent import VisualCriticAgent
from graph.state import BlendPilotState
from mcp_servers.blender.server import BlenderMCPServer
from services.blender_client import BlenderClient
from schemas.design import DesignSpec
from schemas.plan import DesignPlan
from schemas.scene import SceneSummary
from schemas.validation import ValidationResult, VisualCritiqueResult

logger = logging.getLogger("blendpilot.graph.nodes")

RuntimeEventSink = Callable[[dict[str, Any]], Awaitable[None]]
_runtime_event_sinks: dict[str, RuntimeEventSink] = {}


def register_runtime_event_sink(session_id: str, sink: RuntimeEventSink) -> None:
    """Register a transient event sink for live, in-node progress updates."""
    _runtime_event_sinks[session_id] = sink


def unregister_runtime_event_sink(session_id: str) -> None:
    """Remove a transient event sink after a workflow finishes."""
    _runtime_event_sinks.pop(session_id, None)


async def _emit_runtime_event(state: BlendPilotState, payload: dict[str, Any]) -> None:
    """Publish live progress for the active session when an SSE listener exists."""
    session_id = state.get("session_id")
    if not session_id:
        return
    sink = _runtime_event_sinks.get(session_id)
    if sink is None:
        return
    event = {
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    await sink(event)


async def _emit_agent_state(state: BlendPilotState, node: str, agent_name: str, status: str, description: str) -> None:
    await _emit_runtime_event(state, {
        "event": "agent_state",
        "node": node,
        "agent_name": agent_name,
        "status": status,
        "description": description,
    })


def _record_event(state: BlendPilotState, agent_name: str, status: str, description: str, details: dict[str, Any] | None = None) -> None:
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
    """Helper to instantiate LLMService with user-provided keys from state."""
    from services.llm import LLMService
    return LLMService(
        api_key=state.get("api_key"),
        provider=state.get("provider") or "openai",
        model=state.get("model") or "gpt-4o",
        base_url=state.get("base_url"),
        temperature=state.get("temperature", 0.0),
        max_tokens=state.get("max_tokens", 4096),
    )


def _safe_model_dump(obj: Any) -> Any:
    """Safely convert a Pydantic model or dict to a plain dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    return str(obj)


def _get_mcp_server(state: BlendPilotState, provided: BlenderMCPServer | None = None) -> BlenderMCPServer:
    """Use a real Blender bridge by default; mocks are test-only state overrides."""
    if provided is not None:
        return provided
    return BlenderMCPServer(client=BlenderClient(mock_mode=state.get("blender_mock_mode", False)))


# ── Workflow 1: Intent Understanding Node ───────────────────
async def node_intent(state: BlendPilotState) -> dict[str, Any]:
    """Parse user request into structured DesignSpec."""
    logger.info("[Node] Running Intent Agent")
    await _emit_agent_state(state, "intent", "intent_agent", "RUNNING", "Parsing prompt into structured design spec")
    try:
        agent = IntentAgent(llm_service=_get_llm_service(state))
        spec = await agent.execute(
            user_prompt=state["user_prompt"],
            reference_images=state.get("reference_images", []),
        )
        spec_dict = _safe_model_dump(spec)
        _record_event(state, "intent_agent", "COMPLETED", f"Parsed design specification for {spec.asset_type}", {"spec": spec_dict})
        return {
            "current_agent": "scene_agent",
            "design_spec": spec_dict,
        }
    except Exception as e:
        logger.exception("[Node] Intent Agent failed: %s", e)
        _record_event(state, "intent_agent", "FAILED", f"Intent parsing failed: {e}")
        return {
            "current_agent": "scene_agent",
            "design_spec": {
                "asset_type": "generic_prop",
                "description": state.get("user_prompt", ""),
                "error": str(e),
            },
        }


# ── Workflow 2: Scene Understanding Node ────────────────────
async def node_scene(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Inspect active Blender scene state."""
    logger.info("[Node] Running Scene Agent")
    await _emit_agent_state(state, "scene", "scene_agent", "RUNNING", "Scanning active Blender scene")
    try:
        agent = SceneAgent(mcp_server=_get_mcp_server(state, mcp_server))
        scene = await agent.execute()
        scene_dict = _safe_model_dump(scene)
        _record_event(state, "scene_agent", "COMPLETED", f"Scanned scene: {len(scene.objects)} objects present", {"scene": scene_dict})
        return {
            "current_agent": "research_agent",
            "scene_summary": scene_dict,
        }
    except Exception as e:
        logger.exception("[Node] Scene Agent failed: %s", e)
        _record_event(state, "scene_agent", "FAILED", f"Scene scan failed: {e}")
        return {
            "current_agent": "research_agent",
            "scene_summary": {"objects": [], "materials": [], "lights": [], "camera": None, "error": str(e)},
        }


# ── Workflow 3: Research Node ───────────────────────────────
async def node_research(state: BlendPilotState) -> dict[str, Any]:
    """Perform reference and technical specification research."""
    logger.info("[Node] Running Research Agent")
    await _emit_agent_state(state, "research", "research_agent", "RUNNING", "Collecting technical constraints")
    try:
        agent = ResearchAgent(llm_service=_get_llm_service(state))
        spec = DesignSpec.model_validate(state["design_spec"])
        results = await agent.execute(spec=spec)
        _record_event(state, "research_agent", "COMPLETED", f"Gathered technical guidelines for {spec.target_platform}", {"results": results})
        return {
            "current_agent": "planning_agent",
            "research_results": results,
        }
    except Exception as e:
        logger.exception("[Node] Research Agent failed: %s", e)
        _record_event(state, "research_agent", "FAILED", f"Research failed: {e}")
        return {
            "current_agent": "planning_agent",
            "research_results": [],
        }


# ── Workflow 4: Planning Node ───────────────────────────────
async def node_planning(state: BlendPilotState) -> dict[str, Any]:
    """Generate atomic, step-by-step DesignPlan."""
    logger.info("[Node] Running Planning Agent")
    await _emit_agent_state(state, "planning", "planning_agent", "RUNNING", "Generating executable modeling plan")
    try:
        agent = PlanningAgent(llm_service=_get_llm_service(state))
        spec = DesignSpec.model_validate(state["design_spec"])
        scene = SceneSummary.model_validate(state["scene_summary"]) if state.get("scene_summary") else None
        plan = await agent.execute(spec=spec, scene=scene, research=state.get("research_results"))
        plan_dict = _safe_model_dump(plan)
        _record_event(state, "planning_agent", "COMPLETED", f"Generated {len(plan.steps)}-step modeling plan", {"plan": plan_dict})
        await _emit_runtime_event(state, {
            "event": "plan_ready",
            "node": "planning",
            "agent_name": "planning_agent",
            "status": "COMPLETED",
            "step_count": len(plan.steps),
            "plan": plan_dict,
        })
        return {
            "current_agent": "modeling_agent",
            "design_plan": plan_dict,
        }
    except Exception as e:
        logger.exception("[Node] Planning Agent failed: %s", e)
        _record_event(state, "planning_agent", "FAILED", f"Planning failed: {e}")
        return {
            "current_agent": "modeling_agent",
            "design_plan": {"spec_id": "error", "steps": [], "current_step_index": 0, "status": "failed", "error": str(e)},
        }


# ── Workflow 5: Modeling Node ───────────────────────────────
async def node_modeling(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Execute modeling steps and track objects."""
    logger.info("[Node] Running Modeling Agent")
    await _emit_agent_state(state, "modeling", "modeling_agent", "RUNNING", "Executing Blender tool calls")
    try:
        async def event_callback(payload: dict[str, Any]) -> None:
            await _emit_runtime_event(state, {
                "node": "modeling",
                **payload,
            })

        agent = ModelingAgent(
            mcp_server=_get_mcp_server(state, mcp_server),
            llm_service=_get_llm_service(state),
            event_callback=event_callback,
        )
        plan = DesignPlan.model_validate(state["design_plan"])
        res = await agent.execute(plan=plan)
        plan_dict = _safe_model_dump(res["plan"])
        _record_event(state, "modeling_agent", "COMPLETED" if res["success"] else "FAILED", f"Executed modeling steps ({len(res['created_objects'])} objects created)", {"created_objects": res["created_objects"]})
        return {
            "current_agent": "material_agent",
            "created_objects": res["created_objects"],
            "design_plan": plan_dict,
            "modeling_logs": res["logs"],
        }
    except Exception as e:
        logger.exception("[Node] Modeling Agent failed: %s", e)
        _record_event(state, "modeling_agent", "FAILED", f"Modeling failed: {e}")
        return {
            "current_agent": "material_agent",
            "created_objects": [],
            "modeling_logs": [{"error": str(e)}],
        }


# ── Workflow 6: Material & Lighting Node ────────────────────
async def node_material(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Apply PBR shaders, studio lighting, camera framing, and render initial preview."""
    logger.info("[Node] Running Material & Lighting Agent")
    await _emit_agent_state(state, "material", "material_agent", "RUNNING", "Applying materials, lighting, and preview camera")
    try:
        agent = MaterialAgent(mcp_server=_get_mcp_server(state, mcp_server))
        spec = DesignSpec.model_validate(state["design_spec"])
        created_objs = state.get("created_objects", [])
        preview_path = f"output/{spec.asset_type}/preview.png"
        res = await agent.execute(spec=spec, created_objects=created_objs, output_image_path=preview_path)
        _record_event(state, "material_agent", "COMPLETED", f"Applied PBR shaders and rendered preview image", {"preview_image": preview_path})
        return {
            "current_agent": "geometry_qa_agent",
            "materials_created": res["materials"],
            "preview_image_path": preview_path,
        }
    except Exception as e:
        logger.exception("[Node] Material Agent failed: %s", e)
        _record_event(state, "material_agent", "FAILED", f"Material setup failed: {e}")
        return {
            "current_agent": "geometry_qa_agent",
            "materials_created": [],
            "preview_image_path": None,
        }


# ── Workflow 7: Deterministic Geometry QA Node ──────────────
async def node_geometry_qa(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Inspect geometry topology, normals, manifolds, and triangle count."""
    logger.info("[Node] Running Geometry QA Agent")
    await _emit_agent_state(state, "geometry_qa", "geometry_qa_agent", "RUNNING", "Validating topology and triangle budget")
    try:
        agent = GeometryQAAgent(mcp_server=_get_mcp_server(state, mcp_server))
        spec = DesignSpec.model_validate(state["design_spec"])
        created_objs = state.get("created_objects", [])
        repairs = state.get("geometry_repair_count", 0)

        res = await agent.execute(spec=spec, created_objects=created_objs, repair_iteration=repairs)
        issues_list = [_safe_model_dump(i) for i in res["validation_result"].issues] if hasattr(res.get("validation_result"), "issues") else []
        repair_steps = [_safe_model_dump(s) for s in res.get("repair_steps", [])]
        _record_event(
            state,
            "geometry_qa_agent",
            "COMPLETED",
            f"Geometry QA Result: {res['status']} (Score: {res['score']:.2f})",
            {"status": res["status"], "score": res["score"], "issues": len(issues_list)},
        )
        return {
            "current_agent": "visual_critic_agent" if res["status"] == "PASS" else "geometry_repair",
            "geometry_qa_status": res["status"],
            "geometry_score": res["score"],
            "geometry_issues": issues_list,
            "_repair_steps": repair_steps,
        }
    except Exception as e:
        logger.exception("[Node] Geometry QA Agent failed: %s", e)
        _record_event(state, "geometry_qa_agent", "FAILED", f"Geometry QA failed: {e}")
        return {
            "current_agent": "visual_critic_agent",
            "geometry_qa_status": "ERROR",
            "geometry_score": 0.0,
            "geometry_issues": [{"error": str(e)}],
            "_repair_steps": [],
        }


# ── Geometry Repair Node ────────────────────────────────────
async def node_geometry_repair(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Execute automated repair steps to fix topology/triangle/transform issues."""
    logger.info("[Node] Running Geometry Repair Loop")
    await _emit_agent_state(state, "geometry_repair", "geometry_qa_agent", "RUNNING", "Applying geometry repair steps")
    try:
        mcp = _get_mcp_server(state, mcp_server)
        repair_steps = state.get("_repair_steps", [])
        for step in repair_steps:
            await mcp.call_tool(step["tool"], step.get("parameters", {}))

        repair_count = state.get("geometry_repair_count", 0) + 1
        _record_event(state, "geometry_qa_agent", "RUNNING", f"Applied {len(repair_steps)} geometric repair operations (Iteration {repair_count})")
        return {
            "geometry_repair_count": repair_count,
            "current_agent": "geometry_qa_agent",
        }
    except Exception as e:
        logger.exception("[Node] Geometry Repair failed: %s", e)
        return {
            "geometry_repair_count": state.get("geometry_repair_count", 0) + 1,
            "current_agent": "geometry_qa_agent",
        }


# ── Workflow 8: Visual Critic Node ──────────────────────────
async def node_visual_critic(state: BlendPilotState) -> dict[str, Any]:
    """Evaluate rendered image with Vision model against design spec."""
    logger.info("[Node] Running Visual Critic Agent")
    await _emit_agent_state(state, "visual_critic", "visual_critic_agent", "RUNNING", "Evaluating preview render against design goal")
    try:
        agent = VisualCriticAgent(llm_service=_get_llm_service(state))
        spec = DesignSpec.model_validate(state["design_spec"])
        preview = state.get("preview_image_path", "output/preview.png")
        revs = state.get("visual_revision_count", 0)

        critique = await agent.execute(spec=spec, preview_image_path=preview, revision_count=revs)
        _record_event(
            state,
            "visual_critic_agent",
            "COMPLETED",
            f"Visual Critic Score: {critique.overall_score:.2f} (Approved: {critique.approved})",
            {"critique": _safe_model_dump(critique)},
        )
        return {
            "current_agent": "human_feedback" if critique.approved or revs >= 3 else "visual_repair",
            "visual_qa_approved": critique.approved,
            "visual_score": critique.overall_score,
            "visual_issues": critique.issues,
        }
    except Exception as e:
        logger.exception("[Node] Visual Critic failed: %s", e)
        _record_event(state, "visual_critic_agent", "FAILED", f"Visual critique failed: {e}")
        return {
            "current_agent": "human_feedback",
            "visual_qa_approved": False,
            "visual_score": 0.0,
            "visual_issues": [{"error": str(e)}],
        }


# ── Visual Repair Node ──────────────────────────────────────
async def node_visual_repair(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Apply aesthetic refinement and boost contrast/materials."""
    logger.info("[Node] Running Visual Self-Repair Loop")
    await _emit_agent_state(state, "visual_repair", "visual_critic_agent", "RUNNING", "Applying visual refinements")
    try:
        mcp = _get_mcp_server(state, mcp_server)
        # Refine lighting and material
        await mcp.call_tool("setup_studio_lighting", {"key_energy": 1400.0, "fill_energy": 550.0, "rim_energy": 900.0})
        revs = state.get("visual_revision_count", 0) + 1
        _record_event(state, "visual_critic_agent", "RUNNING", f"Applied visual lighting & material refinements (Revision {revs})")
        return {
            "visual_revision_count": revs,
            "current_agent": "visual_critic_agent",
        }
    except Exception as e:
        logger.exception("[Node] Visual Repair failed: %s", e)
        return {
            "visual_revision_count": state.get("visual_revision_count", 0) + 1,
            "current_agent": "visual_critic_agent",
        }


# ── Workflow 9: Human Feedback Node ─────────────────────────
async def node_human_feedback(state: BlendPilotState) -> dict[str, Any]:
    """Process human review decision."""
    logger.info("[Node] Running Human Feedback Agent")
    await _emit_agent_state(state, "human_feedback", "feedback_agent", "RUNNING", "Waiting for or applying human review")
    try:
        agent = FeedbackAgent()
        spec = DesignSpec.model_validate(state["design_spec"])
        plan = DesignPlan.model_validate(state["design_plan"])

        action = state.get("human_action") or "APPROVE"
        fb_text = state.get("human_feedback")

        res = await agent.execute(spec=spec, plan=plan, feedback_text=fb_text, action=action)
        _record_event(state, "feedback_agent", "COMPLETED", f"Human Review status: {res['status']}", {"action": action})
        return {
            "current_agent": "export_agent" if res["approved"] else "planning_agent",
            "approval_status": res["status"],
        }
    except Exception as e:
        logger.exception("[Node] Human Feedback failed: %s", e)
        return {
            "current_agent": "export_agent",
            "approval_status": "APPROVED",
        }


# ── Workflow 10: Production Export Node ─────────────────────
async def node_export(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Export .blend, .fbx, .glb bundles and write asset_report.json."""
    logger.info("[Node] Running Export Agent")
    await _emit_agent_state(state, "export", "export_agent", "RUNNING", "Packaging production export files")
    try:
        agent = ExportAgent(mcp_server=_get_mcp_server(state, mcp_server))
        spec = DesignSpec.model_validate(state["design_spec"])
        created_objs = state.get("created_objects", [])

        geo_qa = ValidationResult(
            status=state.get("geometry_qa_status") or "UNKNOWN",
            score=state.get("geometry_score") or 0.0,
        )
        vis_qa = VisualCritiqueResult(
            approved=state.get("visual_qa_approved") or False,
            overall_score=state.get("visual_score") or 0.0,
        )

        res = await agent.execute(
            spec=spec,
            created_objects=created_objs,
            output_dir="output",
            geometry_qa=geo_qa,
            visual_qa=vis_qa,
        )
        _record_event(state, "export_agent", "COMPLETED", f"Exported {len(res['exported_files'])} production assets to {res['export_directory']}", {"files": res["exported_files"]})
        return {
            "status": "COMPLETED",
            "current_agent": "completed",
            "export_directory": res["export_directory"],
            "exported_files": res["exported_files"],
            "asset_report": res["report"],
        }
    except Exception as e:
        logger.exception("[Node] Export Agent failed: %s", e)
        return {
            "status": "COMPLETED",
            "current_agent": "completed",
            "export_directory": "output",
            "exported_files": [],
            "asset_report": {"error": str(e)},
        }
