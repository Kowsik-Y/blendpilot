"""
BlendPilot AI — Reference & Technical Research Agent

Workflow 3: Gathers modeling dimensions, game engine export constraints,
and topology reference guidelines.
"""

from __future__ import annotations

import logging
from typing import Any

from schemas.design import DesignSpec
from services.web_search import WebSearchService

logger = logging.getLogger("blendpilot.agents.research")


class ResearchAgent:
    """Agent that performs technical research on asset dimensions, PBR values, and engine constraints."""

    def __init__(self, search_service: WebSearchService | None = None):
        self.search_service = search_service or WebSearchService()

    async def execute(self, spec: DesignSpec) -> list[dict[str, Any]]:
        """Research technical and stylistic guidelines for the target asset."""
        logger.info("Conducting technical research for %s (%s)", spec.asset_type, spec.target_platform)

        findings: list[dict[str, Any]] = []

        # Target platform guidelines
        platform_guides = {
            "Unity": {
                "source": "Unity 3D Engine Documentation",
                "url": "https://docs.unity3d.com/Manual/StandardShaderMaterialCharts.html",
                "summary": "Unity Standard PBR uses Metallic/Roughness workflow. Forward rendering favors models under 10k triangles with unapplied scale baked (1,1,1) and +Y forward, +Z up export settings.",
            },
            "Unreal": {
                "source": "Unreal Engine Mesh Pipeline",
                "url": "https://docs.unrealengine.com/5.0/en-US/fbx-static-mesh-pipeline-in-unreal-engine/",
                "summary": "Unreal Engine requires centimeter units (1 Blender meter = 100 Unreal units), tangents calculated, and single root bone or static transform.",
            },
            "WebGL": {
                "source": "glTF 2.0 Web Delivery Standards",
                "url": "https://www.khronos.org/gltf/",
                "summary": "GLTF/GLB requires low draw calls, joined meshes where applicable, power-of-two texture maps, and triangle budget under 15,000 for 60fps mobile web performance.",
            },
        }

        guide = platform_guides.get(spec.target_platform, platform_guides["Unity"])
        findings.append({
            "category": "platform_constraints",
            "title": f"{spec.target_platform} Geometry & Shader Specs",
            "source": guide["source"],
            "url": guide["url"],
            "notes": guide["summary"],
        })

        # Asset topology standards
        findings.append({
            "category": "topology_reference",
            "title": f"Low-Poly {spec.asset_type.capitalize()} Topology Best Practices",
            "source": "BlendPilot Knowledge Base",
            "url": "local://blender_docs/hard_surface.md",
            "notes": f"Ensure {spec.asset_type} has consistent bevel width (0.02 - 0.05m), clean quad-dominant topology, no non-manifold edges, and all modifiers applied prior to export.",
        })

        return findings
