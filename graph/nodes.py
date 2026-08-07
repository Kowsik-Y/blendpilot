"""
BlendPilot AI — LangGraph Node Implementations

Wraps the 10 specialized agent executors into stateful LangGraph node functions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

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
from schemas.design import DesignSpec
from schemas.plan import DesignPlan
from schemas.scene import SceneSummary
from schemas.validation import ValidationResult, VisualCritiqueResult

logger = logging.getLogger("blendpilot.graph.nodes")


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
        provider=state.get("provider") or "openai"
    )



# ── Workflow 1: Intent Understanding Node ───────────────────
async def node_intent(state: BlendPilotState) -> dict[str, Any]:
    """Parse user request into structured DesignSpec."""
    logger.info("[Node] Running Intent Agent")
    agent = IntentAgent(llm_service=_get_llm_service(state))
    spec = await agent.execute(
        user_prompt=state["user_prompt"],
        reference_images=state.get("reference_images", []),
    )
    _record_event(state, "intent_agent", "COMPLETED", f"Parsed design specification for {spec.asset_type}", {"spec": spec.model_dump()})
    return {
        "current_agent": "scene_agent",
        "design_spec": spec.model_dump(),
    }


# ── Workflow 2: Scene Understanding Node ────────────────────
async def node_scene(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Inspect active Blender scene state."""
    logger.info("[Node] Running Scene Agent")
    agent = SceneAgent(mcp_server=mcp_server)
    scene = await agent.execute()
    _record_event(state, "scene_agent", "COMPLETED", f"Scanned scene: {len(scene.objects)} objects present", {"scene": scene.model_dump()})
    return {
        "current_agent": "research_agent",
        "scene_summary": scene.model_dump(),
    }


# ── Workflow 3: Research Node ───────────────────────────────
async def node_research(state: BlendPilotState) -> dict[str, Any]:
    """Perform reference and technical specification research."""
    logger.info("[Node] Running Research Agent")
    agent = ResearchAgent()
    spec = DesignSpec.model_validate(state["design_spec"])
    results = await agent.execute(spec=spec)
    _record_event(state, "research_agent", "COMPLETED", f"Gathered technical guidelines for {spec.target_platform}", {"results": results})
    return {
        "current_agent": "planning_agent",
        "research_results": results,
    }


# ── Workflow 4: Planning Node ───────────────────────────────
async def node_planning(state: BlendPilotState) -> dict[str, Any]:
    """Generate atomic, step-by-step DesignPlan."""
    logger.info("[Node] Running Planning Agent")
    agent = PlanningAgent(llm_service=_get_llm_service(state))
    spec = DesignSpec.model_validate(state["design_spec"])
    scene = SceneSummary.model_validate(state["scene_summary"]) if state.get("scene_summary") else None
    plan = await agent.execute(spec=spec, scene=scene, research=state.get("research_results"))
    _record_event(state, "planning_agent", "COMPLETED", f"Generated {len(plan.steps)}-step modeling plan", {"plan": plan.model_dump()})
    return {
        "current_agent": "modeling_agent",
        "design_plan": plan.model_dump(),
    }


# ── Workflow 5: Modeling Node ───────────────────────────────
async def node_modeling(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Execute modeling steps and track objects."""
    logger.info("[Node] Running Modeling Agent")
    agent = ModelingAgent(mcp_server=mcp_server)
    plan = DesignPlan.model_validate(state["design_plan"])
    res = await agent.execute(plan=plan)
    _record_event(state, "modeling_agent", "COMPLETED" if res["success"] else "FAILED", f"Executed modeling steps ({len(res['created_objects'])} objects created)", {"created_objects": res["created_objects"]})
    return {
        "current_agent": "material_agent",
        "created_objects": res["created_objects"],
        "design_plan": res["plan"].model_dump(),
        "modeling_logs": res["logs"],
    }


# ── Workflow 6: Material & Lighting Node ────────────────────
async def node_material(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Apply PBR shaders, studio lighting, camera framing, and render initial preview."""
    logger.info("[Node] Running Material & Lighting Agent")
    agent = MaterialAgent(mcp_server=mcp_server)
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


# ── Workflow 7: Deterministic Geometry QA Node ──────────────
async def node_geometry_qa(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Inspect geometry topology, normals, manifolds, and triangle count."""
    logger.info("[Node] Running Geometry QA Agent")
    agent = GeometryQAAgent(mcp_server=mcp_server)
    spec = DesignSpec.model_validate(state["design_spec"])
    created_objs = state.get("created_objects", [])
    repairs = state.get("geometry_repair_count", 0)

    res = await agent.execute(spec=spec, created_objects=created_objs, repair_iteration=repairs)
    _record_event(
        state,
        "geometry_qa_agent",
        "COMPLETED",
        f"Geometry QA Result: {res['status']} (Score: {res['score']:.2f})",
        {"status": res["status"], "score": res["score"], "issues": len(res["validation_result"].issues)},
    )
    return {
        "current_agent": "visual_critic_agent" if res["status"] == "PASS" else "geometry_repair",
        "geometry_qa_status": res["status"],
        "geometry_score": res["score"],
        "geometry_issues": [i.model_dump() for i in res["validation_result"].issues],
        "_repair_steps": [s.model_dump() for s in res.get("repair_steps", [])],
    }


# ── Geometry Repair Node ────────────────────────────────────
async def node_geometry_repair(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Execute automated repair steps to fix topology/triangle/transform issues."""
    logger.info("[Node] Running Geometry Repair Loop")
    mcp = mcp_server or BlenderMCPServer()
    repair_steps = state.get("_repair_steps", [])
    for step in repair_steps:
        await mcp.call_tool(step["tool"], step.get("parameters", {}))

    repair_count = state.get("geometry_repair_count", 0) + 1
    _record_event(state, "geometry_qa_agent", "RUNNING", f"Applied {len(repair_steps)} geometric repair operations (Iteration {repair_count})")
    return {
        "geometry_repair_count": repair_count,
        "current_agent": "geometry_qa_agent",
    }


# ── Workflow 8: Visual Critic Node ──────────────────────────
async def node_visual_critic(state: BlendPilotState) -> dict[str, Any]:
    """Evaluate rendered image with Vision model against design spec."""
    logger.info("[Node] Running Visual Critic Agent")
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
        {"critique": critique.model_dump()},
    )
    return {
        "current_agent": "human_feedback" if critique.approved or revs >= 3 else "visual_repair",
        "visual_qa_approved": critique.approved,
        "visual_score": critique.overall_score,
        "visual_issues": critique.issues,
    }


# ── Visual Repair Node ──────────────────────────────────────
async def node_visual_repair(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Apply aesthetic refinement and boost contrast/materials."""
    logger.info("[Node] Running Visual Self-Repair Loop")
    mcp = mcp_server or BlenderMCPServer()
    # Refine lighting and material
    await mcp.call_tool("setup_studio_lighting", {"key_energy": 1400.0, "fill_energy": 550.0, "rim_energy": 900.0})
    revs = state.get("visual_revision_count", 0) + 1
    _record_event(state, "visual_critic_agent", "RUNNING", f"Applied visual lighting & material refinements (Revision {revs})")
    return {
        "visual_revision_count": revs,
        "current_agent": "visual_critic_agent",
    }


# ── Workflow 9: Human Feedback Node ─────────────────────────
async def node_human_feedback(state: BlendPilotState) -> dict[str, Any]:
    """Process human review decision."""
    logger.info("[Node] Running Human Feedback Agent")
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


# ── Workflow 10: Production Export Node ─────────────────────
async def node_export(state: BlendPilotState, mcp_server: BlenderMCPServer | None = None) -> dict[str, Any]:
    """Export .blend, .fbx, .glb bundles and write asset_report.json."""
    logger.info("[Node] Running Export Agent")
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
