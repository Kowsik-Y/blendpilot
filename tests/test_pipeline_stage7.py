"""
BlendPilot AI — Stage 7: Synchronous Pipeline Integration Tests
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from cli import run_sync_pipeline
from schemas.intent import IntentSpec
from schemas.plan_state import ModelingPlan, PlanExecution
from schemas.scene_state import SceneState


@pytest.mark.asyncio
async def test_synchronous_pipeline_integration(mock_bpy):
    """Test that the end-to-end synchronous pipeline connects agents and Blender core correctly."""
    prompt = "Create a red wooden table with four legs"

    # Execute the synchronous pipeline in the mock_bpy environment
    result = await run_sync_pipeline(prompt)

    # 1. Verify parsed intent
    assert result["intent"] is not None
    assert isinstance(result["intent"], IntentSpec)
    assert result["intent"].object_type == "table"
    assert result["intent"].color == "red"
    assert result["intent"].material == "wood"

    # 2. Verify generated modeling plan
    assert result["plan"] is not None
    assert isinstance(result["plan"], ModelingPlan)
    assert len(result["plan"].steps) > 3

    # 3. Verify executed operations & generation result
    assert result["generation"] is not None
    assert isinstance(result["generation"], dict)
    assert result["generation"]["success"] is True
    assert len(result["generation"]["step_executions"]) > 0

    # 4. Verify scene state snapshot collection
    assert result["scene_state"] is not None
    assert isinstance(result["scene_state"], SceneState)
    # The default mock_bpy registered "DefaultCube" in objects_dict
    assert len(result["scene_state"].objects) > 0

    # 5. Verify deliverables and success flag
    assert result["success"] is True
    assert result["blend_path"] is not None
    assert result["blend_path"].endswith("table.blend")
    assert result["preview_path"] is not None
    assert result["preview_path"].endswith("preview.png")
