"""
BlendPilot AI — Stage 5: Planning Agent Tests
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock

from agents.planning_agent import PlanningAgent
from schemas.intent import IntentSpec
from schemas.plan_state import ModelingPlan, ModelingStep
from services.llm import LLMService


def test_validation_unsupported_operation():
    """Test that unsupported operations raise ValidationError."""
    with pytest.raises(ValidationError, match="Unsupported operation"):
        ModelingStep(
            step_id=1,
            operation="unsupported_op_name",
            target="Cube",
        )


def test_validation_non_sequential_step_ids():
    """Test that non-sequential step_ids raise ValidationError."""
    with pytest.raises(ValidationError, match="Plan step_ids must be sequential starting from 1"):
        ModelingPlan(
            steps=[
                ModelingStep(step_id=1, operation="create_primitive", target="Cube"),
                ModelingStep(step_id=3, operation="create_material", target="Material"),
            ]
        )


def test_validation_invalid_dependencies():
    """Test that dependencies on future steps raise ValidationError."""
    with pytest.raises(ValidationError, match="cannot depend on future or self step"):
        ModelingPlan(
            steps=[
                ModelingStep(step_id=1, operation="create_primitive", target="Cube", dependencies=[2]),
                ModelingStep(step_id=2, operation="create_material", target="Material"),
            ]
        )


def test_validation_non_existent_dependencies():
    """Test that dependencies on non-existent steps raise ValidationError."""
    # Step 2 depends on step 0 which is a past step but does not exist
    with pytest.raises(ValidationError, match="depends on non-existent step"):
        ModelingPlan(
            steps=[
                ModelingStep(step_id=1, operation="create_primitive", target="Cube"),
                ModelingStep(step_id=2, operation="create_material", target="Material", dependencies=[0]),
            ]
        )


@pytest.mark.asyncio
async def test_procedural_fallback_planning():
    """Test generating plan using procedural generator."""
    agent = PlanningAgent()
    intent = IntentSpec(
        object_type="table",
        style="low-poly",
        color="brown",
        material="wood",
        required_components=["legs"],
    )
    plan = await agent.execute(intent=intent)
    assert isinstance(plan, ModelingPlan)
    assert len(plan.steps) > 3
    # First step should be creating a primitive table base
    assert plan.steps[0].operation == "create_primitive"
    assert plan.steps[0].target == "table_base"


@pytest.mark.asyncio
async def test_llm_planning_success():
    """Test LLM-driven plan generation when API key is present."""
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.config = MagicMock()
    mock_llm.config.api_key = "fake_key"

    # Mock chat model and structured response returning a valid ModelingPlan
    expected_plan = ModelingPlan(
        steps=[
            ModelingStep(step_id=1, operation="create_primitive", target="chair_base"),
            ModelingStep(step_id=2, operation="create_material", target="wood"),
        ]
    )

    mock_chat = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=expected_plan)
    mock_chat.with_structured_output.return_value = mock_structured
    mock_llm.get_chat_model.return_value = mock_chat

    agent = PlanningAgent(llm_service=mock_llm)
    intent = IntentSpec(object_type="chair")
    plan = await agent.execute(intent=intent)

    assert plan.steps[0].target == "chair_base"
    assert len(plan.steps) == 2
