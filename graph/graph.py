"""
BlendPilot AI — LangGraph Multi-Agent Orchestration StateGraph

Compiles the target architecture pipeline:

    START
      ↓
    intent          (Intent Agent)
      ↓
    planning        (Planning Agent)
      ↓
    generation      (Generation Agent — mesh + materials + lighting + render)
      ↓
    scene_state     (Scene State — Blender context snapshot)
      ↓
    geometry_qa     (Deterministic Geometry QA)
      ↓
    visual_critic   (Vision LLM Critique)
      ↓
    decision        (Decision Agent — APPROVE or REPAIR)
     / \\
 repair  export
   |       |
scene_state END

The repair → scene_state edge closes the self-correction loop.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from graph.nodes import (
    node_executor,
    node_generator,
    node_geometry_qa,
    node_geometry_wait,
    node_vision_critic,
    node_intent,
    node_planner,
    node_scene_state,
    node_render,
    node_decision,
    node_repair,
    node_export,
    node_human_review,
    node_refinement,
)
from graph.persistence import get_checkpointer
from graph.state import BlendPilotState, create_initial_state

logger = logging.getLogger("blendpilot.graph")


def route_from_start(state: BlendPilotState) -> str:
    """Determine the first node based on whether the state already has a scene.
    
    If the user provides a prompt and a scene already exists (and the pipeline
    was previously completed or paused), we route to refinement for modification.
    Otherwise, we start fresh at intent_node.
    """
    if state.get("scene_state") and state.get("status") in ("COMPLETED", "REVIEW_REQUIRED"):
        return "refinement_node"
    return "intent_node"


def route_after_decision(state: BlendPilotState) -> str:
    """Determine the next step after Geometry and Vision QA.
    
    Logic:
      1. If both pass -> export_node
      2. If iteration >= 3 -> export_node (prevent infinite loops)
      3. If fundamentally invalid -> planner_node
      4. Otherwise -> repair_node
    """
    val_report = state.get("validation_report", {})
    vis_report = state.get("vision_report", {})
    
    val_pass = val_report.get("passed", False)
    vis_pass = vis_report.get("overall_result") == "PASS"
    
    if val_pass and vis_pass:
        return "export_node"
        
    if state.get("baseline_mode", False):
        logger.info("Baseline mode enabled. Bypassing repair and routing to export.")
        return "export_node"
        
    iteration_count = state.get("iteration_count", 0)
    if iteration_count >= 3:
        logger.warning("Max iterations reached. Routing to human review.")
        return "human_review_node"
        
    checks = val_report.get("checks", [])
    has_critical = any(c.get("severity") == "critical" for c in checks)
    
    if has_critical:
        logger.warning("Fundamentally invalid scene detected. Re-planning.")
        return "planner_node"
        
    logger.info("Repairable errors found. Routing to repair.")
    return "repair_node"


def build_blendpilot_graph(
    enable_human_interrupt: bool = False,
    checkpointer: Any | None = None,
) -> Any:
    """Construct and compile the BlendPilot multi-agent StateGraph.

    Args:
        enable_human_interrupt: Included for interface compatibility.
        checkpointer: Optional LangGraph checkpointer for persistence.
                      Defaults to the project-configured checkpointer.

    Returns:
        A compiled LangGraph application ready for invocation.
    """
    logger.info("Building BlendPilot Multi-Agent StateGraph...")

    workflow = StateGraph(BlendPilotState)

    # ── Register Nodes ───────────────────────────────────────────────────────
    workflow.add_node("intent_node",      node_intent)
    workflow.add_node("planner_node",     node_planner)
    workflow.add_node("generator_node",   node_generator)
    workflow.add_node("executor_node",    node_executor)
    workflow.add_node("scene_state_node", node_scene_state)
    workflow.add_node("geometry_qa_node", node_geometry_qa)
    workflow.add_node("geometry_wait_node", node_geometry_wait)
    workflow.add_node("render_node",      node_render)
    workflow.add_node("vision_critic_node", node_vision_critic)
    workflow.add_node("decision_node",    node_decision)
    workflow.add_node("repair_node",      node_repair)
    workflow.add_node("export_node",      node_export)
    workflow.add_node("human_review_node", node_human_review)
    workflow.add_node("refinement_node",  node_refinement)

    # ── Sequential Edges (linear spine) ─────────────────────────────────────
    workflow.add_conditional_edges(
        START,
        route_from_start,
        {
            "intent_node": "intent_node",
            "refinement_node": "refinement_node",
        }
    )
    workflow.add_edge("intent_node",       "planner_node")
    workflow.add_edge("planner_node",      "generator_node")
    workflow.add_edge("generator_node",    "executor_node")
    workflow.add_edge("executor_node",     "scene_state_node")
    workflow.add_edge("scene_state_node",  "geometry_qa_node")
    workflow.add_edge("scene_state_node",  "render_node")
    workflow.add_edge("geometry_qa_node",  "geometry_wait_node")
    workflow.add_edge("render_node",       "vision_critic_node")
    workflow.add_edge("geometry_wait_node", "decision_node")
    workflow.add_edge("vision_critic_node", "decision_node")

    # ── Conditional Routing ──────────────────────────────────────────────────
    workflow.add_conditional_edges(
        "decision_node",
        route_after_decision,
        {
            "export_node": "export_node",
            "repair_node": "repair_node",
            "planner_node": "planner_node",
            "human_review_node": "human_review_node",
        }
    )

    # Finish nodes
    workflow.add_edge("export_node", END)
    workflow.add_edge("human_review_node", END)
    workflow.add_edge("repair_node", "scene_state_node")
    workflow.add_edge("refinement_node", "scene_state_node")

    # ── Compile ───────────────────────────────────────────────────────────────
    cp = checkpointer or get_checkpointer()
    app = workflow.compile(checkpointer=cp)

    logger.info("BlendPilot Multi-Agent StateGraph compiled successfully")
    return app


async def run_pipeline(
    user_prompt: str,
    project_id: str | None = None,
    session_id: str | None = None,
    api_key: str | None = None,
    provider: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> BlendPilotState:
    """Convenience entry point to run the full BlendPilot pipeline end-to-end.

    Args:
        user_prompt: The natural language 3D modeling request.
        project_id: Optional project ID for tracking.
        session_id: Optional session ID for checkpointing.
        api_key: LLM API key (OpenAI, Anthropic, etc.).
        provider: LLM provider name (default: "openai").
        overrides: Optional state overrides for testing or config.

    Returns:
        Final BlendPilotState after the pipeline completes.
    """
    initial_state = create_initial_state(
        user_prompt=user_prompt,
        project_id=project_id,
        session_id=session_id,
        api_key=api_key,
        provider=provider,
        overrides=overrides,
    )
    graph = build_blendpilot_graph()
    config = {"configurable": {"thread_id": initial_state["session_id"]}}
    final_state = await graph.ainvoke(initial_state, config=config)
    return final_state
