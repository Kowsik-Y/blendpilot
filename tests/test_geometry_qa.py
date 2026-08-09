"""
BlendPilot AI - Stage 9 Geometry QA tests.
"""

import pytest
from unittest.mock import AsyncMock, patch
from agents.geometry_qa_agent import GeometryQAAgent
from schemas.design import DesignSpec
from schemas.plan import DesignPlan, PlanStep

@pytest.mark.asyncio
async def test_geometry_qa_missing_objects():
    """Test that QA fails if an expected object is missing."""
    mock_mcp = AsyncMock()
    mock_mcp.call_tool = AsyncMock(return_value={
        "success": True,
        "passed": True,
        "result": {
            "passed": True,
            "checks": []
        }
    })
    agent = GeometryQAAgent(mcp_server=mock_mcp)
    spec = DesignSpec(asset_type="wooden table", dimensions={"width":1,"depth":1,"height":1})
    plan = DesignPlan(steps=[
        PlanStep(step_id=1, description="Create tabletop", tool="create_primitive", parameters={"name": "TableTop"}),
        PlanStep(step_id=2, description="Create leg", tool="create_primitive", parameters={"name": "TableLeg"}),
    ])
    created_objects = ["TableTop"]  # TableLeg is missing

    result = await agent.execute(spec=spec, plan=plan, created_objects=created_objects)

    assert result["passed"] is False
    assert result["status"] == "FAIL"
    
    report = result["validation_report"]
    assert report["passed"] is False
    
    # One check should be the missing object check
    missing_check = next((c for c in report["checks"] if c["check_name"] == "missing_required_object"), None)
    assert missing_check is not None
    assert missing_check["object"] == "TableLeg"
    assert missing_check["passed"] is False


@pytest.mark.asyncio
async def test_geometry_qa_passes():
    """Test that QA passes if objects exist and validation returns passed=True."""
    mock_mcp = AsyncMock()
    mock_mcp.call_tool = AsyncMock(return_value={
        "success": True,
        "passed": True,
        "result": {
            "passed": True,
            "checks": [
                {
                    "passed": True,
                    "severity": "high",
                    "check_name": "empty_mesh",
                    "object": "TableTop",
                    "message": "Valid",
                    "suggested_action": ""
                }
            ]
        }
    })
    
    agent = GeometryQAAgent(mcp_server=mock_mcp)
    spec = DesignSpec(asset_type="wooden table", dimensions={"width":1,"depth":1,"height":1})
    plan = DesignPlan(steps=[
        PlanStep(step_id=1, description="Create tabletop", tool="create_primitive", parameters={"name": "TableTop"}),
    ])
    created_objects = ["TableTop"]

    result = await agent.execute(spec=spec, plan=plan, created_objects=created_objects)

    assert result["passed"] is True
    assert result["status"] == "PASS"
    
    report = result["validation_report"]
    assert report["passed"] is True
    assert len(report["checks"]) == 1
    assert report["checks"][0]["check_name"] == "empty_mesh"


@pytest.mark.asyncio
async def test_geometry_qa_mcp_failure():
    """Test that QA fails if MCP validation fails (e.g. duplicate vertices)."""
    mock_mcp = AsyncMock()
    mock_mcp.call_tool = AsyncMock(return_value={
        "success": True,
        "passed": False,
        "result": {
            "passed": False,
            "checks": [
                {
                    "passed": False,
                    "severity": "medium",
                    "check_name": "duplicate_vertices",
                    "object": "TableTop",
                    "message": "Found 4 duplicate vertices",
                    "suggested_action": "Merge by distance"
                }
            ]
        }
    })
    
    agent = GeometryQAAgent(mcp_server=mock_mcp)
    spec = DesignSpec(asset_type="wooden table", dimensions={"width":1,"depth":1,"height":1})
    plan = DesignPlan(steps=[
        PlanStep(step_id=1, description="Create tabletop", tool="create_primitive", parameters={"name": "TableTop"}),
    ])
    created_objects = ["TableTop"]

    result = await agent.execute(spec=spec, plan=plan, created_objects=created_objects)

    assert result["passed"] is False
    assert result["status"] == "FAIL"
    
    report = result["validation_report"]
    assert report["passed"] is False
    assert len(report["checks"]) == 1
    assert report["checks"][0]["check_name"] == "duplicate_vertices"
    assert report["checks"][0]["passed"] is False
