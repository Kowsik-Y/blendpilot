"""
BlendPilot AI — Stage 4: Intent Understanding Agent Tests
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.intent_agent import IntentAgent
from schemas.intent import IntentSpec, IntentDimensions
from services.llm import LLMService


@pytest.mark.asyncio
async def test_normal_request():
    """Test parsing a normal request with explicit detail."""
    agent = IntentAgent()
    spec = await agent.execute(
        user_prompt="Create a brown wooden table 1.2m x 0.8m x 0.75m with legs"
    )
    assert isinstance(spec, IntentSpec)
    assert spec.object_type == "table"
    assert spec.style == "low-poly"
    assert spec.color == "brown"
    assert spec.material == "wood"
    assert "legs" in spec.required_components
    assert spec.dimensions is not None
    assert spec.dimensions.width == 1.2
    assert spec.dimensions.depth == 0.8
    assert spec.dimensions.height == 0.75
    assert spec.is_supported is True


@pytest.mark.asyncio
async def test_missing_optional_information():
    """Test parsing a minimal request with missing optional information."""
    agent = IntentAgent()
    spec = await agent.execute(
        user_prompt="Create a chair"
    )
    assert isinstance(spec, IntentSpec)
    assert spec.object_type == "chair"
    assert spec.color is None
    assert spec.material is None
    assert spec.dimensions is None
    assert spec.is_supported is True


@pytest.mark.asyncio
async def test_unsupported_object():
    """Test that requests for unsupported objects are rejected/flagged."""
    agent = IntentAgent()
    with pytest.raises(ValueError, match="Unsupported object type"):
        await agent.execute(user_prompt="Create a dragon")


@pytest.mark.asyncio
async def test_malformed_llm_response_fallback():
    """Test that malformed/invalid LLM outputs trigger the heuristic parser fallback."""
    mock_llm_service = MagicMock(spec=LLMService)
    mock_llm_service.config = MagicMock()
    mock_llm_service.config.api_key = "fake_api_key"

    # Mock chat model structured output to raise an exception or return None
    mock_chat_model = MagicMock()
    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=None)
    mock_chat_model.with_structured_output.return_value = mock_structured_model
    mock_llm_service.get_chat_model.return_value = mock_chat_model

    agent = IntentAgent(llm_service=mock_llm_service)

    # Should fallback to heuristic parse and return successfully
    spec = await agent.execute(user_prompt="Create a low-poly mug")
    assert isinstance(spec, IntentSpec)
    assert spec.object_type == "mug"
    assert spec.is_supported is True
