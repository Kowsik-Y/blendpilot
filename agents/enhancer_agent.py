"""
BlendPilot — Prompt Enhancer Agent

Workflow Pre-processing: Takes a raw user prompt and expands it with technical
details, stylistic suggestions, and clearer Blender-specific requirements before 
it hits the main intent parsing workflow.
"""

from __future__ import annotations

import logging
from typing import Any

from services.llm import LLMService

logger = logging.getLogger("blendpilot.agents.enhancer")


class EnhancerAgent:
    """Agent that expands a brief user prompt into a detailed 3D modeling prompt."""

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    async def execute(self, user_prompt: str) -> str:
        """Enhance the user prompt with additional technical and aesthetic details."""
        logger.info("Enhancing prompt: %s", user_prompt[:80])

        system_prompt = (
            "You are an expert 3D Technical Artist and Art Director.\n"
            "Your task is to take a user's brief request for a 3D model and expand it into a detailed, "
            "comprehensive prompt suitable for a 3D modeling agent.\n\n"
            "Include details such as:\n"
            "- Specific style (e.g., low-poly, photorealistic, stylized, sci-fi)\n"
            "- Material descriptions (e.g., rough wood, shiny metal, emissive glass)\n"
            "- Plausible scale/dimensions if unspecified\n"
            "- Any necessary geometric features (e.g., bevels, subdivisions)\n\n"
            "Do NOT write a conversation or acknowledge this request. Just return the enhanced prompt."
        )

        user_msg = f"User Request: {user_prompt}\n\nPlease enhance this prompt."

        try:
            response = await self.llm_service.generate(
                prompt=user_msg,
                system_prompt=system_prompt,
            )
            if response:
                enhanced = response.strip()
                logger.info("Enhanced prompt generated.")
                return enhanced
        except Exception as e:
            logger.warning("Prompt enhancement failed: %s", e)

        # Fallback to original prompt if enhancement fails
        return user_prompt
