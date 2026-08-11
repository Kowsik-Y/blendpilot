"""
BlendPilot AI — LangGraph Multi-Agent Orchestration StateGraph

Compiles the complete 10-workflow agent graph with self-correcting QA loops,
visual critique refinement, human interrupt support, and multi-format export.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from graph.nodes import (
    node_enhancer,
    node_export,
    node_geometry_qa,
    node_geometry_repair,
    node_human_feedback,
    node_intent,
    node_material,
    node_modeling,
    node_planning,
    node_research,
    node_scene,
    node_visual_critic,
    node_visual_repair,
)
from graph.persistence import get_checkpointer
from graph.routes import (
    route_after_geometry_qa,
    route_after_human_feedback,
    route_after_visual_critic,
)
from graph.state import BlendPilotState, create_initial_state

logger = logging.getLogger("blendpilot.graph")


def build_blendpilot_graph(
    enable_human_interrupt: bool = False,
    checkpointer: Any | None = None,
) -> Any:
    """Construct and compile the full BlendPilot multi-agent StateGraph."""
    logger.info("Building BlendPilot Multi-Agent StateGraph...")

    workflow = StateGraph(BlendPilotState)

    # ── Register Nodes ──────────────────────────────────────────
    workflow.add_node("enhancer", node_enhancer)
    workflow.add_node("intent", node_intent)
    workflow.add_node("scene", node_scene)
    workflow.add_node("research", node_research)
    workflow.add_node("planning", node_planning)
    workflow.add_node("modeling", node_modeling)
    workflow.add_node("material", node_material)
    workflow.add_node("geometry_qa", node_geometry_qa)
    workflow.add_node("geometry_repair", node_geometry_repair)
    workflow.add_node("visual_critic", node_visual_critic)
    workflow.add_node("visual_repair", node_visual_repair)
    workflow.add_node("human_feedback", node_human_feedback)
    workflow.add_node("export", node_export)

    # ── Add Sequential Edges ────────────────────────────────────
    workflow.add_edge(START, "enhancer")
    workflow.add_edge("enhancer", "intent")
    workflow.add_edge("intent", "scene")
    workflow.add_edge("scene", "research")
    workflow.add_edge("research", "planning")
    workflow.add_edge("planning", "modeling")
    workflow.add_edge("modeling", "material")
    workflow.add_edge("material", "geometry_qa")

    # ── Add Conditional & Self-Repair Loops ─────────────────────
    # 1. Deterministic Geometry QA Branch
    workflow.add_conditional_edges(
        "geometry_qa",
        route_after_geometry_qa,
        {
            "visual_critic": "visual_critic",
            "geometry_repair": "geometry_repair",
        },
    )
    workflow.add_edge("geometry_repair", "geometry_qa")

    # 2. Vision Critic Self-Repair Branch
    workflow.add_conditional_edges(
        "visual_critic",
        route_after_visual_critic,
        {
            "human_feedback": "human_feedback",
            "visual_repair": "visual_repair",
        },
    )
    workflow.add_edge("visual_repair", "visual_critic")

    # 3. Human Review & Feedback Branch
    workflow.add_conditional_edges(
        "human_feedback",
        route_after_human_feedback,
        {
            "export": "export",
            "planning": "planning",
        },
    )

    # 4. Final Export
    workflow.add_edge("export", END)

    # Compile with optional checkpointer and human interrupt
    interrupt_before = ["human_feedback"] if enable_human_interrupt else []
    cp = checkpointer or get_checkpointer()

    app = workflow.compile(
        checkpointer=cp,
        interrupt_before=interrupt_before,
    )
    logger.info("BlendPilot Multi-Agent StateGraph compiled successfully")
    return app


async def run_pipeline(
    user_prompt: str,
    project_id: str | None = None,
    session_id: str | None = None,
    overrides: dict[str, Any] | None = None,
    mock_mode: bool = False,
) -> BlendPilotState:
    """Convenience entry point to run the entire BlendPilot pipeline end-to-end."""
    runtime_overrides = {**(overrides or {}), "blender_mock_mode": mock_mode}
    initial_state = create_initial_state(
        user_prompt=user_prompt,
        project_id=project_id,
        session_id=session_id,
        overrides=runtime_overrides,
    )
    graph = build_blendpilot_graph(enable_human_interrupt=False)
    config = {"configurable": {"thread_id": initial_state["session_id"]}, "recursion_limit": 150}
    final_state = await graph.ainvoke(initial_state, config=config)
    return final_state
