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
    node_decision,
    node_export,
    node_generation,
    node_geometry_qa,
    node_intent,
    node_planning,
    node_repair,
    node_scene_state,
    node_visual_critic,
)
from graph.persistence import get_checkpointer
from graph.routes import route_after_decision
from graph.state import BlendPilotState, create_initial_state

logger = logging.getLogger("blendpilot.graph")


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
    workflow.add_node("intent",        node_intent)
    workflow.add_node("planning",      node_planning)
    workflow.add_node("generation",    node_generation)
    workflow.add_node("scene_state",   node_scene_state)
    workflow.add_node("geometry_qa",   node_geometry_qa)
    workflow.add_node("visual_critic", node_visual_critic)
    workflow.add_node("decision_node", node_decision)
    workflow.add_node("repair",        node_repair)
    workflow.add_node("export",        node_export)

    # ── Sequential Edges (linear spine) ─────────────────────────────────────
    workflow.add_edge(START,          "intent")
    workflow.add_edge("intent",       "planning")
    workflow.add_edge("planning",     "generation")
    workflow.add_edge("generation",   "scene_state")
    workflow.add_edge("scene_state",  "geometry_qa")
    workflow.add_edge("geometry_qa",  "visual_critic")
    workflow.add_edge("visual_critic","decision_node")

    # ── Conditional Routing: Decision → repair or export ─────────────────────
    workflow.add_conditional_edges(
        "decision_node",
        route_after_decision,
        {
            "repair": "repair",
            "export": "export",
        },
    )

    # ── Self-Correction Loop: repair → scene_state (re-validation) ───────────
    workflow.add_edge("repair", "scene_state")

    # ── Terminal Edge ─────────────────────────────────────────────────────────
    workflow.add_edge("export", END)

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
