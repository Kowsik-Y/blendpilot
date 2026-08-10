"""
BlendPilot AI — LLM Provider Service

Unified interface for LLM providers (OpenAI, Anthropic, Google Gemini, Ollama, etc.)
used by all agents for text generation, plan synthesis, copilot chat, and vision critique.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("blendpilot.services.llm")


class LLMConfig(BaseModel):
    """Configuration for an LLM provider."""

    provider: str = Field(default="groq", description="LLM provider: openai, anthropic, groq, custom")
    model: str = Field(default="llama-3.3-70b-versatile", description="Model name")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    api_key: str = Field(default="", description="API key (loaded from env or request)")
    base_url: str | None = Field(default=None, description="Custom API base URL")


class LLMService:
    """Unified LLM client with provider abstraction."""

    VISION_MODELS: dict[str, str] = {
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-20241022",
        "groq": "llama-3.2-90b-vision-preview",
    }

    def __init__(
        self,
        provider: str = "groq",
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.0,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        # Auto-resolve API keys from environment if not explicitly passed
        resolved_key = (
            api_key
            or os.environ.get("GROQ_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or ""
        )
        resolved_provider = provider
        if not api_key:
            if os.environ.get("GROQ_API_KEY"):
                resolved_provider = "groq"
                resolved_key = os.environ.get("GROQ_API_KEY", "")
            elif os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
                resolved_provider = "anthropic"
                resolved_key = os.environ.get("ANTHROPIC_API_KEY", "")

        self.config = LLMConfig(
            provider=resolved_provider,
            model=model,
            temperature=temperature,
            api_key=resolved_key,
            base_url=base_url or os.environ.get("LLM_BASE_URL"),
        )

    def get_chat_model(self) -> Any:
        """Return a LangChain ChatModel instance for text generation."""
        if self.config.provider == "openai":
            from langchain_openai import ChatOpenAI
            kwargs: dict[str, Any] = {
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }
            if self.config.api_key:
                kwargs["api_key"] = self.config.api_key
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            return ChatOpenAI(**kwargs)

        elif self.config.provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            kwargs = {
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }
            if self.config.api_key:
                kwargs["api_key"] = self.config.api_key
            return ChatAnthropic(**kwargs)
            
        elif self.config.provider == "groq":
            from langchain_groq import ChatGroq
            kwargs = {
                "model_name": self.config.model,
                "temperature": self.config.temperature,
            }
            if self.config.api_key:
                kwargs["api_key"] = self.config.api_key
            return ChatGroq(**kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Execute async text generation using the configured LLM provider."""
        if not self.config.api_key and self.config.provider != "custom":
            logger.debug("No API key configured for LLMService; returning empty for heuristic fallback")
            return ""

        try:
            model = self.get_chat_model()
            messages = []
            if system_prompt:
                from langchain_core.messages import SystemMessage
                messages.append(SystemMessage(content=system_prompt))
            from langchain_core.messages import HumanMessage
            messages.append(HumanMessage(content=prompt))

            response = await model.ainvoke(messages)
            return str(response.content)
        except Exception as e:
            logger.warning("LLM generation encountered an error: %s", e)
            return ""

    async def generate_vision(self, prompt: str, image_paths: list[str]) -> str:
        """Execute multimodal vision evaluation using real vision models."""
        if not self.config.api_key or not image_paths:
            return ""

        try:
            content_parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

            for img_path in image_paths:
                if os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        })

            if self.config.provider == "groq":
                import groq
                client = groq.AsyncGroq(api_key=self.config.api_key)
                model_name = "qwen/qwen3.6-27b"
                res = await client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": content_parts}]
                )
                return str(res.choices[0].message.content)

            from langchain_core.messages import HumanMessage
            model = self.get_chat_model()
            msg = HumanMessage(content=content_parts)
            res = await model.ainvoke([msg])
            return str(res.content)
        except Exception as e:
            logger.warning("Vision LLM evaluation failed: %s", e)
            raise RuntimeError(f"Vision LLM evaluation failed: {e}")
