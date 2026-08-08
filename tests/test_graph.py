"""
BlendPilot AI — Tests for LangGraph Multi-Agent Orchestration & State Machine
"""

import pytest
from unittest.mock import MagicMock

from graph.graph import build_blendpilot_graph, run_pipeline
from graph.routes import route_after_decision
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


def test_conditional_routing_decision():
    # Test APPROVE decision
    state_approve: BlendPilotState = {"decision": "APPROVE"}
    assert route_after_decision(state_approve) == "export"

    # Test REPAIR decision
    state_repair: BlendPilotState = {"decision": "REPAIR", "priority_issue": "geometry"}
    assert route_after_decision(state_repair) == "repair"


def test_graph_compilation():
    graph = build_blendpilot_graph()
    assert graph is not None


@pytest.mark.asyncio
async def test_end_to_end_pipeline_execution():
    result = await run_pipeline(
        user_prompt="Create a low-poly barrel for Unity. Dimensions: 0.5m x 0.5m x 0.8m. Under 4,000 triangles.",
    )
    assert result["status"] == "COMPLETED"
    assert result["current_agent"] == "completed"
