"""
BlendPilot AI — Design Intent Understanding Agent

Workflow 1: Converts natural-language design requests into structured DesignSpec models.
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

        # Parse with rule-based heuristics first for deterministic fallback & fast parsing
        fallback_spec = self._heuristic_parse(user_prompt, reference_images or [])

        # Try LLM structured parsing if configured
        if self.llm_service and self.llm_service.config.api_key:
            try:
                system_prompt = INTENT_SYSTEM_PROMPT.format(
                    format_instructions="Return a valid JSON matching the DesignSpec schema."
                )
                user_msg = INTENT_USER_PROMPT.format(
                    user_prompt=user_prompt,
                    reference_info=f"Reference images: {len(reference_images or [])}",
                )
                response = await self.llm_service.generate(
                    prompt=user_msg,
                    system_prompt=system_prompt,
                    response_format={"type": "json_object"},
                )
                # Clean JSON fences if present
                clean_json = re.sub(r"^```json\s*|\s*```$", "", response.strip(), flags=re.MULTILINE)
                data = json.loads(clean_json)
                data["user_prompt"] = user_prompt
                if reference_images:
                    data["reference_images"] = reference_images
                return DesignSpec.model_validate(data)
            except Exception as e:
                logger.warning("LLM intent parsing failed (%s), using robust fallback parser", e)

        return fallback_spec

    def _heuristic_parse(self, user_prompt: str, reference_images: list[str]) -> DesignSpec:
        """Robust heuristic parser for common game assets, furniture, sci-fi props."""
        lower = user_prompt.lower()

        # Determine Asset Type
        asset_type = "generic_prop"
        if "table" in lower:
            asset_type = "table"
        elif "chair" in lower or "stool" in lower:
            asset_type = "chair"
        elif "crate" in lower or "box" in lower:
            asset_type = "crate"
        elif "barrel" in lower or "drum" in lower:
            asset_type = "barrel"
        elif "door" in lower:
            asset_type = "door"
        elif "barrier" in lower:
            asset_type = "barrier"
        elif "pylon" in lower:
            asset_type = "pylon"
        elif "pedestal" in lower:
            asset_type = "pedestal"
        elif "shelf" in lower or "bookshelf" in lower:
            asset_type = "bookshelf"
        elif "lamp" in lower or "light" in lower:
            asset_type = "street_lamp"
        elif "chest" in lower:
            asset_type = "chest"
        elif "piston" in lower:
            asset_type = "piston"
        elif "wheel" in lower:
            asset_type = "robot_wheel"
        elif "valve" in lower:
            asset_type = "pipe_valve"

        # Style
        style = "low-poly"
        if "sci-fi" in lower or "scifi" in lower or "futuristic" in lower:
            style = "sci-fi"
        elif "medieval" in lower or "fantasy" in lower:
            style = "medieval"
        elif "industrial" in lower or "cyberpunk" in lower:
            style = "industrial"
        elif "stylized" in lower:
            style = "stylized"

        # Target Platform
        target_platform = "Unity"
        if "unreal" in lower:
            target_platform = "Unreal"
        elif "web" in lower or "threejs" in lower or "webgl" in lower:
            target_platform = "WebGL"
        elif "godot" in lower:
            target_platform = "Godot"

        # Triangle Limit extraction
        triangle_limit = 8000
        tri_match = re.search(r"(\d+[\d,]*)\s*(?:triangles|tris|poly|polygons)", lower)
        if tri_match:
            try:
                triangle_limit = int(tri_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # Dimensions extraction (e.g., "1 m × 0.7 m × 0.6 m" or "1x0.7x0.6" or "1.2m x 0.8m x 0.75m")
        dim_match = re.search(
            r"(\d+(?:\.\d+)?)\s*m?\s*[×x*]\s*(\d+(?:\.\d+)?)\s*m?\s*[×x*]\s*(\d+(?:\.\d+)?)\s*m?",
            lower,
        )
        if dim_match:
            try:
                w, d, h = float(dim_match.group(1)), float(dim_match.group(2)), float(dim_match.group(3))
                dimensions = Dimensions(width=w, depth=d, height=h)
            except Exception:
                dimensions = self._default_dimensions(asset_type)
        else:
            dimensions = self._default_dimensions(asset_type)

        # Materials extraction
        materials = []
        if "red" in lower:
            materials.append("red_matte")
        if "metallic" in lower or "metal" in lower or "dark metal" in lower:
            materials.append("dark_metal")
        if "emissive" in lower or "blue emissive" in lower or "glow" in lower:
            materials.append("blue_emissive")
        if "wood" in lower or "wooden" in lower:
            materials.append("wood_grain")
        if "glass" in lower:
            materials.append("glass")
        if not materials:
            materials = ["base_gray_pbr"]

        # Export format
        export_format = "FBX"
        if "glb" in lower or "gltf" in lower:
            export_format = "GLB"
        elif "obj" in lower:
            export_format = "OBJ"

        return DesignSpec(
            asset_type=asset_type,
            style=style,
            dimensions=dimensions,
            triangle_limit=triangle_limit,
            target_platform=target_platform,
            materials=materials,
            export_format=export_format,
            description=user_prompt,
            reference_images=reference_images,
        )

    def _default_dimensions(self, asset_type: str) -> Dimensions:
        """Sensible physical dimensions per category."""
        defaults = {
            "table": Dimensions(width=1.2, depth=0.8, height=0.75),
            "chair": Dimensions(width=0.45, depth=0.45, height=0.85),
            "crate": Dimensions(width=1.0, depth=0.7, height=0.6),
            "barrel": Dimensions(width=0.5, depth=0.5, height=0.8),
            "door": Dimensions(width=0.9, depth=0.1, height=2.1),
            "bookshelf": Dimensions(width=0.8, depth=0.3, height=1.6),
            "street_lamp": Dimensions(width=0.4, depth=0.4, height=2.8),
            "chest": Dimensions(width=0.8, depth=0.5, height=0.5),
            "barrier": Dimensions(width=1.5, depth=0.3, height=0.8),
            "pylon": Dimensions(width=0.6, depth=0.6, height=2.2),
            "pedestal": Dimensions(width=0.7, depth=0.7, height=1.0),
            "robot_wheel": Dimensions(width=0.4, depth=0.4, height=0.2),
            "pipe_valve": Dimensions(width=0.5, depth=0.3, height=0.5),
            "piston": Dimensions(width=0.3, depth=0.3, height=0.8),
        }
        return defaults.get(asset_type, Dimensions(width=1.0, depth=1.0, height=1.0))
