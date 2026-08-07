"""
BlendPilot AI — LLM Provider Service

Unified interface for LLM providers (OpenAI, Anthropic, etc.)
used by all agents for text generation and vision tasks.

Phase: 4 (interface defined, implementation pending)
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("blendpilot.services.llm")


class LLMConfig(BaseModel):
    """Configuration for an LLM provider."""

    provider: str = Field(default="openai", description="LLM provider: openai, anthropic")
    model: str = Field(default="gpt-4o", description="Model name")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    api_key: str = Field(default="", description="API key (loaded from env)")


class LLMService:
    """Unified LLM client with provider abstraction.

    Provides a consistent interface for text generation and
    vision tasks across different LLM providers.

    Usage:
        llm = LLMService(provider="openai", model="gpt-4o")
        chat_model = llm.get_chat_model()  # LangChain ChatModel
        vision_model = llm.get_vision_model()  # Vision-capable model
    """

    # Provider → model mapping for vision tasks
    VISION_MODELS: dict[str, str] = {
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-20250514",
    }

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o",
        temperature: float = 0.0,
        api_key: str | None = None,
    ):
        self.config = LLMConfig(
            provider=provider,
            model=model,
            temperature=temperature,
            api_key=api_key or "",
        )

    def get_chat_model(self) -> Any:
        """Return a LangChain ChatModel instance for text generation.

        Returns:
            ChatOpenAI or ChatAnthropic instance.

        Raises:
            ImportError: If the required LangChain package is not installed.
            ValueError: If the provider is not supported.
        """
        if self.config.provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
        elif self.config.provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")

    def get_vision_model(self) -> Any:
        """Return a vision-capable LLM model for visual critique.

        Used by the Visual Critic Agent (Workflow 8) to evaluate
        rendered preview images.

        Returns:
            A vision-capable ChatModel instance.
        """
        vision_model = self.VISION_MODELS.get(self.config.provider)
        if vision_model is None:
            raise ValueError(
                f"No vision model available for provider: {self.config.provider}"
            )

        logger.info(
            "Creating vision model: %s/%s",
            self.config.provider, vision_model,
        )

        if self.config.provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=vision_model,
                temperature=0.0,
                max_tokens=self.config.max_tokens,
            )
        elif self.config.provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=vision_model,
                temperature=0.0,
                max_tokens=self.config.max_tokens,
            )
        else:
            raise ValueError(f"Unsupported provider for vision: {self.config.provider}")
