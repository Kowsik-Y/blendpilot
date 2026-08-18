"""
BlendPilot — Scene Understanding Agent

Workflow 2: Inspects active Blender scene state, builds structured SceneSummary,
and verifies existing scene context.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp_servers.blender.server import BlenderMCPServer
from schemas.scene import ObjectInfo, SceneSummary

logger = logging.getLogger("blendpilot.agents.scene")


class SceneAgent:
    """Agent responsible for inspecting and understanding active Blender scene state."""

    def __init__(self, mcp_server: BlenderMCPServer | None = None):
        self.mcp_server = mcp_server or BlenderMCPServer()

    async def execute(self, params: dict[str, Any] | None = None) -> SceneSummary:
        """Query Blender for current scene objects, active selections, lighting, and camera."""
        logger.info("Scanning Blender scene state...")
        try:
            res = await self.mcp_server.call_tool("get_scene_summary", params or {})
            if res.get("success") and "scene" in res:
                return SceneSummary.model_validate(res["scene"])
        except Exception as e:
            logger.warning(
                "Live scene inspection encountered error (%s), returning clean baseline", e)

        # Baseline clean scene summary
        return SceneSummary(
            objects=[],
            total_triangles=0,
            has_camera=False,
            has_lights=False,
            active_object=None,
        )
