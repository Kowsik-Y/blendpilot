"""
BlendPilot AI — Reference & Technical Research Agent

Workflow 3: Uses LLM to generate contextual research findings based on the
specific asset + style combination. Falls back to curated knowledge base.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from schemas.design import DesignSpec
from services.llm import LLMService
from services.web_search import WebSearchService

logger = logging.getLogger("blendpilot.agents.research")


class ResearchAgent:
    """Agent that performs technical research on asset dimensions, PBR values, and engine constraints."""

    def __init__(
        self,
        search_service: WebSearchService | None = None,
        llm_service: LLMService | None = None,
    ):
        self.search_service = search_service or WebSearchService()
        self.llm_service = llm_service

    async def execute(self, spec: DesignSpec) -> list[dict[str, Any]]:
        """Research technical and stylistic guidelines for the target asset."""
        logger.info("Conducting technical research for %s (%s)", spec.asset_type, spec.target_platform)

        findings: list[dict[str, Any]] = []

        # Always include platform-specific knowledge base entries
        findings.extend(self._get_platform_guidelines(spec))

        # Try LLM-generated contextual research if available
        if self.llm_service and self.llm_service.config.api_key:
            try:
                llm_findings = await self._llm_research(spec)
                if llm_findings:
                    findings.extend(llm_findings)
                    logger.info("LLM generated %d additional research findings", len(llm_findings))
                    return findings
            except Exception as e:
                logger.warning("LLM research generation failed (%s), using knowledge base only", e)

        # Add static topology best practices
        findings.append({
            "category": "topology_reference",
            "title": f"Low-Poly {spec.asset_type.capitalize()} Topology Best Practices",
            "source": "BlendPilot Knowledge Base",
            "url": "local://blender_docs/hard_surface.md",
            "notes": (
                f"Ensure {spec.asset_type} has consistent bevel width (0.02 - 0.05m), "
                f"clean quad-dominant topology, no non-manifold edges, and all modifiers "
                f"applied prior to export."
            ),
        })

        return findings

    async def _llm_research(self, spec: DesignSpec) -> list[dict[str, Any]] | None:
        """Use LLM to generate contextual research findings for the specific asset."""
        prompt = (
            f"You are a 3D technical director researching best practices for creating a "
            f"{spec.style} {spec.asset_type} model for {spec.target_platform}.\n\n"
            f"Asset details:\n"
            f"- Dimensions: {spec.dimensions.width}m × {spec.dimensions.depth}m × {spec.dimensions.height}m\n"
            f"- Triangle budget: {spec.triangle_limit}\n"
            f"- Materials: {', '.join(spec.materials)}\n"
            f"- Export format: {spec.export_format}\n\n"
            f"Generate 3-5 specific technical research findings as a JSON array. Each finding:\n"
            f'{{"category": str, "title": str, "source": str, "notes": str}}\n\n'
            f"Cover: topology techniques, PBR material values, edge flow strategies, "
            f"engine-specific optimization tips, and reference dimension ratios."
        )

        response = await self.llm_service.generate(
            prompt=prompt,
            system_prompt=(
                "You are a Blender 3D expert. Return a JSON array of research findings. "
                "Each finding has: category, title, source, notes. Be specific with numeric "
                "values (metallic ranges, roughness values, bevel widths, vertex counts)."
            ),
            response_format={"type": "json_object"},
        )

        if not response:
            return None

        try:
            clean = re.sub(r"^```json\s*|\s*```$", "", response.strip(), flags=re.MULTILINE)
            data = json.loads(clean)
            # Handle both {"findings": [...]} and [...] formats
            if isinstance(data, dict) and "findings" in data:
                return data["findings"]
            elif isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # LLM might return a single-key wrapper
                for key, val in data.items():
                    if isinstance(val, list):
                        return val
            return None
        except Exception as e:
            logger.warning("Failed to parse LLM research response: %s", e)
            return None

    def _get_platform_guidelines(self, spec: DesignSpec) -> list[dict[str, Any]]:
        """Get curated platform-specific technical guidelines."""
        platform_guides = {
            "Unity": {
                "source": "Unity 3D Engine Documentation",
                "url": "https://docs.unity3d.com/Manual/StandardShaderMaterialCharts.html",
                "summary": (
                    "Unity Standard PBR uses Metallic/Roughness workflow. Forward rendering "
                    "favors models under 10k triangles with unapplied scale baked (1,1,1) "
                    "and +Y forward, +Z up export settings."
                ),
            },
            "Unreal": {
                "source": "Unreal Engine Mesh Pipeline",
                "url": "https://docs.unrealengine.com/5.0/en-US/fbx-static-mesh-pipeline-in-unreal-engine/",
                "summary": (
                    "Unreal Engine requires centimeter units (1 Blender meter = 100 Unreal units), "
                    "tangents calculated, and single root bone or static transform."
                ),
            },
            "WebGL": {
                "source": "glTF 2.0 Web Delivery Standards",
                "url": "https://www.khronos.org/gltf/",
                "summary": (
                    "GLTF/GLB requires low draw calls, joined meshes where applicable, "
                    "power-of-two texture maps, and triangle budget under 15,000 for "
                    "60fps mobile web performance."
                ),
            },
        }

        guide = platform_guides.get(spec.target_platform, platform_guides["Unity"])
        return [{
            "category": "platform_constraints",
            "title": f"{spec.target_platform} Geometry & Shader Specs",
            "source": guide["source"],
            "url": guide["url"],
            "notes": guide["summary"],
        }]
