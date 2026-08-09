import pytest
from agents.repair_agent import RepairAgent

@pytest.mark.asyncio
async def test_repair_agent_mock_mode_geometry():
    """Test that RepairAgent generates a correct RepairPlan in mock mode for geometry issues."""
    agent = RepairAgent(mock_mode=True)
    
    val_report = {
        "passed": False,
        "checks": [
            {
                "passed": False,
                "severity": "medium",
                "check_name": "duplicate_vertices",
                "object": "Mug",
                "message": "Duplicate vertices found"
            }
        ]
    }
    
    result = await agent.execute(
        intent={},
        validation_report=val_report,
        vision_report={"overall_result": "PASS"},
        scene_state={}
    )
    
    assert result["success"] is True
    assert result["ops_executed"] == 0  # mock mode doesn't execute
    
    plan = result["repair_plan"]
    assert "steps" in plan
    assert len(plan["steps"]) == 1
    
    step = plan["steps"][0]
    assert step["affected_object"] == "Mug"
    assert step["corrective_operation"] == "edit_mesh"
    assert step["parameters"]["operation"] == "merge_doubles"

@pytest.mark.asyncio
async def test_repair_agent_mock_mode_vision():
    """Test that RepairAgent generates a correct RepairPlan in mock mode for vision issues."""
    agent = RepairAgent(mock_mode=True)
    
    vis_report = {
        "overall_result": "FAIL",
        "obvious_visual_errors": ["Lighting is too dark"]
    }
    
    result = await agent.execute(
        intent={},
        validation_report={"passed": True, "checks": []},
        vision_report=vis_report,
        scene_state={}
    )
    
    assert result["success"] is True
    
    plan = result["repair_plan"]
    assert len(plan["steps"]) == 2  # lighting fix + preview render
    
    step1 = plan["steps"][0]
    assert step1["corrective_operation"] == "setup_studio_lighting"
    
    step2 = plan["steps"][1]
    assert step2["corrective_operation"] == "render_preview"
