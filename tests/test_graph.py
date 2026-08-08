"""
BlendPilot AI — Tests for Stage 8 LangGraph Orchestration & State Machine
"""

import pytest
from unittest.mock import MagicMock

from graph.graph import build_blendpilot_graph, run_pipeline
from graph.state import BlendPilotState, create_initial_state


def test_initial_state_factory():
    """Verify create_initial_state populates the new Stage 8 keys correctly."""
    state = create_initial_state(
        user_prompt="Create a red wooden table with four legs",
        reference_images=["img1.png"],
    )
    assert state["user_prompt"] == "Create a red wooden table with four legs"
    assert state["status"] == "RUNNING"
    assert state["reference_images"] == ["img1.png"]
    
    # Verify new orchestration keys are initialized
    assert "intent" in state
    assert state["intent"] is None
    assert "plan" in state
    assert state["plan"] is None
    assert "executable_operations" in state
    assert state["executable_operations"] == []
    assert "execution_result" in state
    assert state["execution_result"] is None
    assert "scene_state" in state
    assert state["scene_state"] is None
    assert "errors" in state
    assert state["errors"] == []
    assert "iteration_count" in state
    assert state["iteration_count"] == 0


def test_graph_compilation():
    """Verify build_blendpilot_graph compiles node connections successfully."""
    graph = build_blendpilot_graph()
    assert graph is not None
    
    # Check that registered nodes contain our Stage 8 keys/flow
    node_names = set(graph.nodes.keys())
    assert "intent_node" in node_names
    assert "planner_node" in node_names
    assert "generator_node" in node_names
    assert "executor_node" in node_names
    assert "scene_state_node" in node_names


@pytest.mark.asyncio
async def test_end_to_end_graph_execution(mock_bpy):
    """Verify the sequential LangGraph executes end-to-end and updates all state variables."""
    result = await run_pipeline(
        user_prompt="Create a red wooden table with four legs",
    )
    
    # Verify execution state
    assert result["status"] == "COMPLETED"
    assert result["current_agent"] == "END"
    assert result["error"] is None
    assert result["iteration_count"] == 1
    
    # Verify state persistence:
    # 1. Intent Spec
    assert result["intent"] is not None
    assert result["intent"]["object_type"] == "table"
    assert result["intent"]["color"] == "red"
    assert result["intent"]["material"] == "wood"

    # 2. Modeling Plan
    assert result["plan"] is not None
    assert len(result["plan"]["steps"]) > 0

    # 3. Executable Operations
    assert result["executable_operations"] is not None
    assert len(result["executable_operations"]) == len(result["plan"]["steps"])
    assert result["executable_operations"][0]["operation"] == "create_primitive"

    # 4. Execution Result
    assert result["execution_result"] is not None
    assert result["execution_result"]["success"] is True
    assert len(result["created_objects"]) > 0
    assert len(result["materials_created"]) > 0

    # 5. Scene State snapshot
    assert result["scene_state"] is not None
    # We mocked active object creation, so the scene summary contains objects
    assert len(result["scene_state"]["objects"]) > 0
    assert result["scene_state"]["has_camera"] is True
