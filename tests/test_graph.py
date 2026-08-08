"""
BlendPilot AI — Tests for LangGraph Multi-Agent Orchestration & State Machine
"""

import pytest

from graph.graph import build_blendpilot_graph, run_pipeline
from graph.routes import (
    route_after_geometry_qa,
    route_after_human_feedback,
    route_after_visual_critic,
)
from graph.state import BlendPilotState, create_initial_state


def test_initial_state_factory():
    state = create_initial_state(
        user_prompt="Create a sci-fi crate",
        reference_images=["img1.png"],
    )
    assert state["user_prompt"] == "Create a sci-fi crate"
    assert state["status"] == "RUNNING"
    assert state["reference_images"] == ["img1.png"]
    assert state["max_geometry_repairs"] == 3


def test_conditional_routing_geometry_qa():
    # Pass status
    state_pass: BlendPilotState = {"geometry_qa_status": "PASS", "geometry_repair_count": 0}
    assert route_after_geometry_qa(state_pass) == "visual_critic"

    # Fail status under limit
    state_fail: BlendPilotState = {"geometry_qa_status": "FAIL", "geometry_repair_count": 0, "max_geometry_repairs": 3}
    assert route_after_geometry_qa(state_fail) == "geometry_repair"

    # Fail status max repairs exceeded
    state_max: BlendPilotState = {"geometry_qa_status": "FAIL", "geometry_repair_count": 3, "max_geometry_repairs": 3}
    assert route_after_geometry_qa(state_max) == "visual_critic"


def test_conditional_routing_visual_critic():
    state_approved: BlendPilotState = {"visual_qa_approved": True, "visual_revision_count": 0}
    assert route_after_visual_critic(state_approved) == "human_review"

    state_needs_work: BlendPilotState = {"visual_qa_approved": False, "visual_revision_count": 0, "max_visual_revisions": 3}
    assert route_after_visual_critic(state_needs_work) == "visual_repair"


def test_conditional_routing_human_feedback():
    state_ok: BlendPilotState = {"approval_status": "APPROVED"}
    assert route_after_human_feedback(state_ok) == "export"

    state_rev: BlendPilotState = {"approval_status": "REVISION_REQUESTED"}
    assert route_after_human_feedback(state_rev) == "planning"


def test_graph_compilation():
    graph = build_blendpilot_graph(enable_human_interrupt=False)
    assert graph is not None


@pytest.mark.asyncio
async def test_end_to_end_pipeline_execution():
    result = await run_pipeline(
        user_prompt="Create a low-poly barrel for Unity. Dimensions: 0.5m x 0.5m x 0.8m. Under 4,000 triangles.",
        mock_mode=True,
    )
    assert result["status"] == "COMPLETED"
    assert result["current_agent"] == "completed"
    assert len(result["exported_files"]) >= 3
    assert result["asset_report"] is not None
