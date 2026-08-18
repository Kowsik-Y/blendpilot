"""
BlendPilot — Visual Critic and Aesthetic Self-Repair Agent

Workflow 8: Evaluates rendered 2D preview with Vision LLM against DesignSpec,
computes visual critique score, and triggers self-repair actions.
Uses generate_vision() for real multi-modal critique when API key is available.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from prompts.visual_critic import VISUAL_CRITIC_SYSTEM_PROMPT, VISUAL_CRITIC_USER_PROMPT
from schemas.design import DesignSpec
from schemas.validation import VisualCritiqueResult
from services.llm import LLMService

logger = logging.getLogger("blendpilot.agents.visual_critic")


class VisualCriticAgent:
    """Agent that performs multi-modal visual QA critique and aesthetic self-repair."""

    MAX_VISUAL_REVISIONS: int = 3
    APPROVAL_THRESHOLD: float = 0.75

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    async def execute(
        self,
        spec: DesignSpec,
        preview_image_path: str,
        revision_count: int = 0,
    ) -> VisualCritiqueResult:
        """Analyze rendered preview image and return visual critique, score, and revision actions."""
        logger.info("Critiquing visual quality for %s (revision %d)...",
                    spec.asset_type, revision_count)

        # Try real Vision LLM critique first
        if self.llm_service and self.llm_service.config.api_key:
            try:
                critique = await self._llm_vision_critique(spec, preview_image_path, revision_count)
                if critique:
                    logger.info("Vision LLM critique: score=%.2f approved=%s",
                                critique.overall_score, critique.approved)
                    return critique
            except Exception as e:
                logger.warning(
                    "Vision LLM critique failed (%s), falling back to text-only LLM", e)

        # Fallback: text-only LLM critique (no image)
        try:
            critique = await self._llm_text_critique(spec, revision_count)
            if critique:
                return critique
        except Exception as e:
            logger.error("Text-only LLM critique failed (%s)", e)
            raise RuntimeError(
                f"Failed to generate VisualCritiqueResult via LLM: {e}")

        raise RuntimeError(
            "LLM failed to return a valid VisualCritiqueResult and no heuristic fallback is permitted.")

    async def _llm_vision_critique(
        self,
        spec: DesignSpec,
        preview_image_path: str,
        revision_count: int,
    ) -> VisualCritiqueResult | None:
        """Use multi-modal Vision LLM to evaluate the rendered preview image."""
        import os
        if not os.path.exists(preview_image_path):
            logger.warning(
                "Preview image not found at %s, skipping vision critique", preview_image_path)
            return None

        prompt = (
            f"You are evaluating a 3D rendered preview image for a {spec.asset_type} "
            f"(style: {spec.style}, dimensions: {spec.dimensions.width}m × {spec.dimensions.depth}m × {spec.dimensions.height}m).\n\n"
            f"Evaluate the render on these criteria:\n"
            f"1. Silhouette clarity and proportions\n"
            f"2. Material/shader quality (PBR fidelity)\n"
            f"3. Lighting quality (3-point studio lighting)\n"
            f"4. Edge quality (bevel catches, smooth shading)\n"
            f"5. Overall aesthetic appeal for {spec.target_platform} game engine\n\n"
            f"This is revision {revision_count}.\n\n"
            f"Return JSON: {{\"approved\": bool, \"overall_score\": 0.0-1.0, "
            f"\"aesthetic_score\": 0.0-1.0, \"spec_compliance_score\": 0.0-1.0, "
            f"\"strengths\": [str], \"issues\": [str], \"suggested_actions\": [str]}}"
        )

        response = await self.llm_service.generate_vision(
            prompt=prompt,
            image_paths=[preview_image_path],
        )

        if not response:
            return None

        try:
            clean = re.sub(r"^```json\s*|\s*```$", "",
                           response.strip(), flags=re.MULTILINE)
            data = json.loads(clean)
            return VisualCritiqueResult.model_validate(data)
        except Exception as e:
            logger.warning("Failed to parse vision critique response: %s", e)
            return None

    async def _llm_text_critique(
        self,
        spec: DesignSpec,
        revision_count: int,
    ) -> VisualCritiqueResult | None:
        """Use text-only LLM for critique evaluation when no preview image is available."""
        system_prompt = VISUAL_CRITIC_SYSTEM_PROMPT.format(
            format_instructions="Return a valid JSON matching VisualCritiqueResult schema."
        )
        user_msg = (
            f"Evaluate a {spec.style} {spec.asset_type} 3D model:\n"
            f"- Dimensions: {spec.dimensions.width}m × {spec.dimensions.depth}m × {spec.dimensions.height}m\n"
            f"- Materials: {', '.join(spec.materials)}\n"
            f"- Target: {spec.target_platform}\n"
            f"- Triangle limit: {spec.triangle_limit}\n"
            f"- Revision count: {revision_count}\n\n"
            f"Based on standard 3D quality criteria, provide your critique as JSON."
        )

        response = await self.llm_service.generate(
            prompt=user_msg,
            system_prompt=system_prompt,
            response_format={"type": "json_object"},
        )

        if not response:
            return None

        try:
            clean = re.sub(r"^```json\s*|\s*```$", "",
                           response.strip(), flags=re.MULTILINE)
            data = json.loads(clean)
            return VisualCritiqueResult.model_validate(data)
        except Exception as e:
            logger.warning("Failed to parse text critique response: %s", e)
            return None
