"""
BlendPilot AI — Stage 6: Generation Agent Tests
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from agents.generation_agent import GenerationAgent
from schemas.intent import IntentSpec
from schemas.plan_state import ModelingPlan, ModelingStep


@pytest.mark.asyncio
async def test_generation_agent_mapping_to_core():
    """Verify that the correct core operations are selected and executed with mapped parameters."""
    agent = GenerationAgent(mock_mode=False)

    spec = IntentSpec(object_type="table", style="low-poly")
    plan = ModelingPlan(
        steps=[
            ModelingStep(
                step_id=1,
                operation="create_primitive",
                target="tabletop",
                parameters={"primitive_type": "cube", "dimensions": [1.2, 0.8, 0.05]},
            ),
            ModelingStep(
                step_id=2,
                operation="create_material",
                target="wood",
                parameters={"base_color": [0.4, 0.25, 0.15, 1.0], "metallic": 0.0},
            ),
            ModelingStep(
                step_id=3,
                operation="assign_material",
                target="tabletop",
                parameters={"material_name": "wood"},
                dependencies=[1, 2],
            ),
            ModelingStep(
                step_id=4,
                operation="add_modifier",
                target="tabletop",
                parameters={"modifier_type": "BEVEL", "name": "Bevel"},
                dependencies=[1],
            ),
            ModelingStep(
                step_id=5,
                operation="render_preview",
                target="Render",
                parameters={"output_path": "output/table/preview.png"},
            ),
        ]
    )

    # Patch core module functions to assert they are selected correctly
    with patch("core.objects.create_primitive", return_value={"success": True, "object_name": "tabletop"}) as mock_create_prim, \
         patch("core.materials.create_material", return_value={"success": True, "material_name": "wood"}) as mock_create_mat, \
         patch("core.materials.assign_material", return_value={"success": True}) as mock_assign_mat, \
         patch("core.modifiers.add_modifier", return_value={"success": True}) as mock_add_mod, \
         patch("core.rendering.render_preview", return_value={"success": True}) as mock_render:

        result = await agent.execute(spec=spec, plan=plan)

        # Assert selection and parameter mappings
        mock_create_prim.assert_called_once_with(
            primitive_type="cube",
            name="tabletop",
            dimensions=(1.2, 0.8, 0.05),
            location=(0.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
        )
        mock_create_mat.assert_called_once_with(
            name="wood",
            base_color=(0.4, 0.25, 0.15, 1.0),
            metallic=0.0,
            roughness=0.5,
            emission_color=None,
            emission_strength=0.0,
        )
        mock_assign_mat.assert_called_once_with(
            object_name="tabletop",
            material_name="wood",
        )
        mock_add_mod.assert_called_once_with(
            object_name="tabletop",
            modifier_type="BEVEL",
            modifier_name="Bevel",
            params=None,
        )
        mock_render.assert_called_once_with(
            output_path="output/table/preview.png",
            resolution_x=1024,
            resolution_y=1024,
            samples=64,
        )

        # Assert return format and execution representation
        assert result["success"] is True
        assert "tabletop" in result["created_objects"]
        assert "wood" in result["materials_created"]
        assert len(result["step_executions"]) == 5
        assert result["step_executions"][0]["operation"] == "create_primitive"
        assert result["step_executions"][0]["success"] is True
