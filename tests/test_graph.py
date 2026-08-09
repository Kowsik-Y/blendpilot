"""
BlendPilot AI — Tests for Stage 8 LangGraph Orchestration & State Machine
"""

import pytest
from unittest.mock import MagicMock

from graph.graph import build_blendpilot_graph, run_pipeline
from graph.state import BlendPilotState, create_initial_state

@pytest.fixture(autouse=True)
def mock_mcp_call_tool():
    """Mock the MCP tool call to avoid real HTTP requests during graph tests."""
    from unittest.mock import AsyncMock, patch
    with patch("mcp_servers.blender.server.BlenderMCPServer.call_tool", new_callable=AsyncMock) as mock_call_tool:
        mock_call_tool.return_value = {
            "success": True,
            "passed": True,
            "result": {"passed": True, "checks": []}
        }
        yield mock_call_tool


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
    # Instead of checking property 'has_camera' which doesn't serialize by default, check 'camera'
    assert result["scene_state"].get("camera") is not None


@pytest.mark.asyncio
async def test_graph_state_preservation():
    """Verify that user prompt, intent, and plans are preserved properly."""
    result = await run_pipeline(
        user_prompt="Create a green metal box",
    )
    
    assert result["user_prompt"] == "Create a green metal box"
    assert result["intent"] is not None
    assert result["plan"] is not None
    assert result["iteration_count"] == 1
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_intent_node_failure():
    """Simulate a failure in intent parsing to verify error handling."""
    # This might require patching IntentAgent to raise an error
    # Let's mock the IntentAgent's execute method to raise an Exception
    from unittest.mock import AsyncMock, patch
    
    with patch("graph.nodes.IntentAgent") as MockAgentClass:
        mock_instance = MockAgentClass.return_value
        mock_instance.execute = AsyncMock(side_effect=ValueError("Simulated intent failure"))
        
        result = await run_pipeline("Create a failed item")
        
        assert "Simulated intent failure" in result["errors"]
        # The graph continues to planner using a fallback spec when intent fails in node_intent
        # However, the node_intent sets error in state
        assert result["intent"]["object_type"] == "generic_prop"
        
        # It still completes the pipeline but with the fallback
        assert result["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_executor_node_mock_mode():
    """Verify that in mock mode, executor node returns execution_result correctly."""
    result = await run_pipeline(
        user_prompt="Create a blue wooden table",
    )
    
    execution_res = result.get("execution_result")
    assert execution_res is not None
    assert execution_res["success"] is True
    assert "step_executions" in execution_res
    assert len(execution_res["step_executions"]) > 0
@pytest.mark.asyncio
async def test_multi_turn_refinement():
    """Verify that a second prompt routes to refinement_node."""
    from graph.graph import build_blendpilot_graph
    from graph.state import create_initial_state
    
    # 1. Compile graph once so checkpointer is shared
    graph = build_blendpilot_graph()
    session_id = "test_multi_turn_session"
    config = {"configurable": {"thread_id": session_id}}
    
    # 2. First run generates the scene
    initial_state = create_initial_state(user_prompt="Create a stool", session_id=session_id)
    result1 = await graph.ainvoke(initial_state, config=config)
    assert result1["status"] == "COMPLETED"
    
    # 3. Second run with same session_id should refine. 
    # We only pass the updated user_prompt to trigger refinement.
    result2 = await graph.ainvoke({"user_prompt": "Make it taller"}, config=config)
    
    # Check that refinement happened (status will end up as COMPLETED again)
    assert result2["status"] == "COMPLETED"
    
    # In mock mode, the refinement heuristic should have added a set_transform repair plan
    events = result2.get("events", [])
    refinement_events = [e for e in events if e.get("agent_name") == "refinement_agent"]
    assert len(refinement_events) > 0
    assert "modification_plan" in refinement_events[0]["details"]
