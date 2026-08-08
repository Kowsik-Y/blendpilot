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

        # Try LLM structured parsing if configured
        if self.llm_service and self.llm_service.config.api_key:
            try:
                spec = await self._llm_structured_parse(user_prompt, reference_images or [])
                if spec:
                    logger.info("LLM structured output produced DesignSpec for: %s", spec.asset_type)
                    return spec
            except Exception as e:
                logger.warning("LLM intent parsing failed (%s), using heuristic fallback", e)

        # Fallback: enhanced heuristic parser
        return self._heuristic_parse(user_prompt, reference_images or [])

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
                reference_info=f"Reference images: {len(reference_images)}",
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
                reference_info=f"Reference images: {len(reference_images)}",
            )
            response = await self.llm_service.generate(
                prompt=user_msg,
                system_prompt=system_prompt,
                response_format={"type": "json_object"},
            )
            if response:
                clean_json = re.sub(r"^```json\s*|\s*```$", "", response.strip(), flags=re.MULTILINE)
                data = json.loads(clean_json)
                data["user_prompt"] = user_prompt
                if reference_images:
                    data["reference_images"] = reference_images
                return DesignSpec.model_validate(data)
        except Exception as e:
            logger.warning("JSON fallback parsing also failed: %s", e)

        return None

    def _heuristic_parse(self, user_prompt: str, reference_images: list[str]) -> DesignSpec:
        """Enhanced heuristic parser for a wide range of 3D assets."""
        lower = user_prompt.lower()

        # Determine Asset Type — expanded vocabulary
        asset_type = "generic_prop"
        asset_keywords = {
            "table": "table", "desk": "table", "bench": "table",
            "chair": "chair", "stool": "chair", "seat": "chair",
            "crate": "crate", "box": "crate", "container": "crate",
            "barrel": "barrel", "drum": "barrel", "keg": "barrel",
            "door": "door", "gate": "door",
            "barrier": "barrier", "fence": "barrier", "wall": "barrier",
            "pylon": "pylon", "tower": "pylon", "antenna": "pylon", "beacon": "pylon",
            "pedestal": "pedestal", "pillar": "pedestal", "column": "pedestal",
            "shelf": "bookshelf", "bookshelf": "bookshelf", "cabinet": "bookshelf",
            "lamp": "street_lamp", "lantern": "street_lamp", "light": "street_lamp",
            "chest": "chest", "trunk": "chest", "coffer": "chest",
            "piston": "piston", "engine": "piston", "gear": "piston",
            "wheel": "robot_wheel", "tire": "robot_wheel",
            "valve": "pipe_valve", "pipe": "pipe_valve",
            "sword": "sword", "blade": "sword", "katana": "sword", "dagger": "sword", "weapon": "sword",
            "tree": "tree", "plant": "tree", "bush": "tree", "foliage": "tree",
            "car": "vehicle", "vehicle": "vehicle", "truck": "vehicle", "bus": "vehicle",
            "spaceship": "spaceship", "ship": "spaceship", "shuttle": "spaceship", "aircraft": "spaceship",
            "robot": "robot", "mech": "robot", "android": "robot",
            "crystal": "crystal", "gem": "crystal", "diamond": "crystal",
            "rock": "rock", "stone": "rock", "boulder": "rock",
            "shield": "shield", "armor": "shield",
            "helmet": "helmet", "mask": "helmet",
            "potion": "potion", "flask": "potion", "bottle": "potion",
            "house": "building", "building": "building", "cabin": "building",
        }
        for keyword, atype in asset_keywords.items():
            if keyword in lower:
                asset_type = atype
                break

        # Style
        style = "low-poly"
        style_keywords = {
            "sci-fi": "sci-fi", "scifi": "sci-fi", "futuristic": "sci-fi", "cyber": "sci-fi", "neon": "sci-fi",
            "medieval": "medieval", "fantasy": "medieval", "gothic": "medieval", "ancient": "medieval",
            "industrial": "industrial", "cyberpunk": "industrial", "steampunk": "industrial",
            "stylized": "stylized", "cartoon": "stylized", "toon": "stylized",
            "realistic": "realistic", "photorealistic": "realistic", "detailed": "realistic",
            "minimalist": "minimalist", "minimal": "minimalist", "clean": "minimalist",
        }
        for keyword, stype in style_keywords.items():
            if keyword in lower:
                style = stype
                break

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

        # Materials extraction — expanded
        materials = []
        material_keywords = {
            "red": "red_matte", "blue": "blue_matte", "green": "green_matte",
            "gold": "gold_metal", "silver": "silver_metal", "bronze": "bronze_metal",
            "metallic": "dark_metal", "metal": "dark_metal", "dark metal": "dark_metal",
            "emissive": "blue_emissive", "glow": "blue_emissive", "neon": "neon_emissive",
            "wood": "wood_grain", "wooden": "wood_grain", "oak": "wood_grain", "pine": "wood_grain",
            "glass": "glass", "transparent": "glass", "crystal": "glass",
            "stone": "stone_rough", "concrete": "stone_rough", "rock": "stone_rough",
            "rust": "rusted_metal", "rusted": "rusted_metal", "corroded": "rusted_metal",
            "leather": "leather_brown", "fabric": "fabric_cloth",
            "ice": "ice_transparent", "frost": "ice_transparent",
            "lava": "lava_emissive", "magma": "lava_emissive",
            "chrome": "chrome_mirror", "mirror": "chrome_mirror",
        }
        for keyword, mat in material_keywords.items():
            if keyword in lower and mat not in materials:
                materials.append(mat)
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
            "sword": Dimensions(width=0.08, depth=0.04, height=1.15),
            "tree": Dimensions(width=1.5, depth=1.5, height=3.2),
            "vehicle": Dimensions(width=2.2, depth=4.4, height=1.3),
            "spaceship": Dimensions(width=3.0, depth=6.0, height=2.0),
            "robot": Dimensions(width=0.8, depth=0.8, height=1.8),
            "crystal": Dimensions(width=0.3, depth=0.3, height=0.6),
            "rock": Dimensions(width=1.0, depth=1.0, height=0.7),
            "shield": Dimensions(width=0.6, depth=0.1, height=0.8),
            "helmet": Dimensions(width=0.3, depth=0.3, height=0.35),
            "potion": Dimensions(width=0.1, depth=0.1, height=0.25),
            "building": Dimensions(width=4.0, depth=4.0, height=3.5),
        }
        return defaults.get(asset_type, Dimensions(width=1.0, depth=1.0, height=1.0))
