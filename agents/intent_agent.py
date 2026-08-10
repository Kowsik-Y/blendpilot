"""
BlendPilot AI — Design Intent Understanding Agent

Workflow 1: Converts natural-language design requests into structured DesignSpec models
using LangChain structured output (with_structured_output) for reliable LLM-driven parsing.
Falls back to an enhanced heuristic parser when no API key is configured.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from prompts.intent import INTENT_SYSTEM_PROMPT, INTENT_USER_PROMPT
from schemas.design import DesignSpec, Dimensions
from services.llm import LLMService

logger = logging.getLogger("blendpilot.agents.intent")


class IntentAgent:
    """Agent that extracts a structured 3D DesignSpec from natural-language instructions."""

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    async def execute(
        self,
        user_prompt: str,
        reference_images: list[str] | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> DesignSpec:
        """Parse natural language request into a validated DesignSpec."""
        logger.info("Parsing design intent for: %s", user_prompt[:80])

        # If user provided programmatic overrides, apply them directly
        if overrides:
            try:
                spec = DesignSpec.model_validate({**overrides, "user_prompt": user_prompt})
                return spec
            except ValidationError:
                pass

        # Strict LLM parsing, no heuristic fallback
        try:
            spec = await self._llm_structured_parse(user_prompt, reference_images or [])
            if spec:
                logger.info("LLM structured output produced DesignSpec for: %s", spec.asset_type)
                return spec
        except Exception as e:
            logger.error("LLM intent parsing failed (%s)", e)
            raise RuntimeError(f"Failed to generate DesignSpec via LLM: {e}")

<<<<<<< HEAD
        # Try LLM structured parsing if configured
        if self.llm_service and self.llm_service.config.api_key:
            try:
                system_prompt = INTENT_SYSTEM_PROMPT.format(
                    format_instructions="Return a valid JSON matching the DesignSpec schema."
                )
                user_msg = INTENT_USER_PROMPT.format(
                    user_prompt=user_prompt,
                    reference_images=f"{len(reference_images or [])} reference image(s)",
                )
                response = await self.llm_service.generate(
                    prompt=user_msg,
                    system_prompt=system_prompt,
                    response_format={"type": "json_object"},
                )
                # Clean JSON fences if present
                clean_json = response.strip()
                json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_json)
                if json_match:
                    clean_json = json_match.group(1).strip()
                else:
                    brace_match = re.search(r"(\{[\s\S]*\})", clean_json)
                    if brace_match:
                        clean_json = brace_match.group(1).strip()

=======
        raise RuntimeError("LLM failed to return a valid DesignSpec and no fallback is permitted.")

    async def _llm_structured_parse(
        self,
        user_prompt: str,
        reference_images: list[str],
    ) -> DesignSpec | None:
        """Use LangChain structured output to parse the user prompt into a DesignSpec."""
        try:
            chat_model = self.llm_service.get_chat_model()

            # Use with_structured_output for reliable JSON extraction
            structured_model = chat_model.with_structured_output(DesignSpec)

            system_prompt = INTENT_SYSTEM_PROMPT.format(
                format_instructions="Extract a DesignSpec from the user's 3D modeling request. "
                "Include asset_type, style, dimensions (width/depth/height in meters), "
                "triangle_limit, target_platform, materials list, export_format, and description."
            )
            user_msg = INTENT_USER_PROMPT.format(
                user_prompt=user_prompt,
                reference_images=len(reference_images),
            )

            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_msg),
            ]

            result = await structured_model.ainvoke(messages)

            # Ensure required fields are populated
            if result and isinstance(result, DesignSpec):
                if not result.description:
                    result.description = user_prompt
                if reference_images:
                    result.reference_images = reference_images
                return result

        except Exception as e:
            logger.warning("Structured output parsing failed: %s", e)

        # Fallback: try raw JSON parsing from LLM
        try:
            system_prompt = INTENT_SYSTEM_PROMPT.format(
                format_instructions="Return a valid JSON matching the DesignSpec schema."
            )
            user_msg = INTENT_USER_PROMPT.format(
                user_prompt=user_prompt,
                reference_images=len(reference_images),
            )
            response = await self.llm_service.generate(
                prompt=user_msg,
                system_prompt=system_prompt,
                response_format={"type": "json_object"},
            )
            if response:
                clean_json = re.sub(r"^```json\s*|\s*```$", "", response.strip(), flags=re.MULTILINE)
>>>>>>> 9960c34c885b76ae6a6056cb373b1205a98fc89e
                data = json.loads(clean_json)
                data["user_prompt"] = user_prompt
                if reference_images:
                    data["reference_images"] = reference_images
                return DesignSpec.model_validate(data)
        except Exception as e:
            logger.warning("JSON fallback parsing also failed: %s", e)

        return None

