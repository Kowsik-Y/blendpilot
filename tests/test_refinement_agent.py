import pytest
from agents.refinement_agent import RefinementAgent

@pytest.mark.asyncio
async def test_refinement_agent_mock_color():
    """Test that RefinementAgent handles color changes using heuristics."""
    agent = RefinementAgent(mock_mode=True)
    
    scene_state = {
        "objects": [{"name": "TableBody"}]
    }
    
    result = await agent.execute(
        user_prompt="Make it blue",
        scene_state=scene_state
    )
    
    assert result["success"] is True
    plan = result["modification_plan"]
    
    assert len(plan["steps"]) == 2
    assert plan["steps"][0]["corrective_operation"] == "create_material"
    assert plan["steps"][1]["corrective_operation"] == "assign_material"
    assert plan["steps"][1]["affected_object"] == "TableBody"

@pytest.mark.asyncio
async def test_refinement_agent_mock_scale():
    """Test that RefinementAgent handles scale changes using heuristics."""
    agent = RefinementAgent(mock_mode=True)
    
    scene_state = {
        "objects": [{"name": "TableBody"}]
    }
    
    result = await agent.execute(
        user_prompt="Make it taller",
        scene_state=scene_state
    )
    
    assert result["success"] is True
    plan = result["modification_plan"]
    
    assert len(plan["steps"]) == 1
    assert plan["steps"][0]["corrective_operation"] == "set_transform"
    assert plan["steps"][0]["parameters"]["scale"] == [1.0, 1.0, 1.5]
