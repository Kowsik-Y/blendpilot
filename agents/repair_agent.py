"""
BlendPilot AI — Unified Repair Agent

Phase 3: Takes the prioritized issue context from the Decision Agent and
executes targeted MCP tool operations to fix the mesh or aesthetic quality,
replacing the dispersed node_geometry_repair / node_visual_repair inline logic.

Repairs are ranked by priority_issue:
  - "geometry" → Fix topology, normals, triangle budget
  - "visual"   → Refine lighting, boost material emission/contrast
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from mcp_servers.blender.server import BlenderMCPServer
from schemas.design import DesignSpec
from services.llm import LLMService

logger = logging.getLogger("blendpilot.agents.repair")

_REPAIR_SYSTEM_PROMPT = """
You are the Repair Agent for a BlendPilot 3D asset generation pipeline.

You receive:
- priority_issue: "geometry" or "visual"
- The list of specific issues reported by the QA validators
- The list of created object names
- The DesignSpec (asset_type, style, triangle_limit)

Your task: generate a JSON array of targeted MCP tool calls to fix the issues.

Available MCP tools:
- edit_mesh: {"object_name": str, "operation": "recalculate_normals" | "apply_transforms" | "merge_doubles"}
- add_modifier: {"object_name": str, "modifier_type": "DECIMATE", "modifier_name": str, "properties": {"ratio": float}}
- apply_modifier: {"object_name": str, "modifier_name": str}
- create_material: {"name": str, "base_color": [r,g,b,a], "metallic": float, "roughness": float, "emission_color": [r,g,b,a], "emission_strength": float}
- assign_material: {"object_name": str, "material_name": str}
- setup_studio_lighting: {"key_energy": float, "fill_energy": float, "rim_energy": float}
- render_preview: {"output_path": str, "resolution_x": int, "resolution_y": int, "samples": int}

Rules:
- For geometry issues: fix normals first, then triangle count, then transforms
- For visual issues: boost lighting contrast and re-render preview
- Keep the list minimal and targeted (max 5 operations)
- Always end visual repairs with a render_preview step

Respond ONLY with a JSON array of tool call objects:
[{"tool": "<name>", "parameters": {<params>}}, ...]
"""


class RepairAgent:
    """Unified repair agent that fixes geometry or visual issues via MCP calls."""

    def __init__(
        self,
        mcp_server: BlenderMCPServer | None = None,
        llm_service: LLMService | None = None,
    ):
        self.mcp_server = mcp_server or BlenderMCPServer()
        self.llm_service = llm_service

    async def execute(
        self,
        spec: DesignSpec,
        created_objects: list[str],
        priority_issue: str,
        geometry_issues: list[dict[str, Any]],
        visual_issues: list[str],
        preview_image_path: str,
        geometry_repair_count: int,
        visual_revision_count: int,
    ) -> dict[str, Any]:
        """Execute targeted repair operations and return updated counters.

        Args:
            spec: DesignSpec for asset context.
            created_objects: Object names currently in the scene.
            priority_issue: "geometry" or "visual" (from DecisionAgent).
            geometry_issues: List of geometry issue dicts from GeometryQAAgent.
            visual_issues: List of visual issue strings from VisualCriticAgent.
            preview_image_path: Path to re-render preview to after visual repair.
            geometry_repair_count: Current geometry repair iteration.
            visual_revision_count: Current visual revision iteration.

        Returns:
            dict with: success, ops_executed, new_preview_image_path,
                       geometry_repair_count, visual_revision_count
        """
        logger.info(
            "RepairAgent executing — priority: %s | objects: %s",
            priority_issue,
            created_objects,
        )

        # Try LLM-powered targeted repair plan
        if self.llm_service and self.llm_service.config.api_key:
            try:
                tool_calls = await self._llm_generate_repairs(
                    spec=spec,
                    created_objects=created_objects,
                    priority_issue=priority_issue,
                    geometry_issues=geometry_issues,
                    visual_issues=visual_issues,
                    preview_image_path=preview_image_path,
                )
                if tool_calls:
                    return await self._execute_tool_calls(
                        tool_calls=tool_calls,
                        priority_issue=priority_issue,
                        preview_image_path=preview_image_path,
                        geometry_repair_count=geometry_repair_count,
                        visual_revision_count=visual_revision_count,
                    )
            except Exception as exc:
                logger.warning("LLM repair planning failed (%s), using heuristic", exc)

        # Heuristic fallback
        tool_calls = self._heuristic_repairs(
            spec=spec,
            created_objects=created_objects,
            priority_issue=priority_issue,
            geometry_issues=geometry_issues,
            preview_image_path=preview_image_path,
        )
        return await self._execute_tool_calls(
            tool_calls=tool_calls,
            priority_issue=priority_issue,
            preview_image_path=preview_image_path,
            geometry_repair_count=geometry_repair_count,
            visual_revision_count=visual_revision_count,
        )

    async def _llm_generate_repairs(
        self,
        spec: DesignSpec,
        created_objects: list[str],
        priority_issue: str,
        geometry_issues: list[dict[str, Any]],
        visual_issues: list[str],
        preview_image_path: str,
    ) -> list[dict[str, Any]]:
        """Ask the LLM to generate a targeted list of MCP repair calls."""
        user_msg = (
            f"Asset: {spec.asset_type} (style: {spec.style}, "
            f"triangle_limit: {spec.triangle_limit})\n"
            f"Objects in scene: {created_objects}\n"
            f"Priority issue: {priority_issue}\n"
            f"Geometry issues: {json.dumps(geometry_issues[:5])}\n"
            f"Visual issues: {visual_issues}\n"
            f"Preview output path: {preview_image_path}\n\n"
            "Generate a minimal, targeted list of MCP repair operations."
        )

        response = await self.llm_service.generate(
            prompt=user_msg,
            system_prompt=_REPAIR_SYSTEM_PROMPT.strip(),
            response_format={"type": "json_object"},
        )

        if not response:
            raise ValueError("Empty LLM response")

        clean = re.sub(r"^```json\s*|\s*```$", "", response.strip(), flags=re.MULTILINE)
        parsed = json.loads(clean)

        # Handle both {"tool_calls": [...]} and [...] response shapes
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return parsed.get("tool_calls", parsed.get("operations", []))
        return []

    def _heuristic_repairs(
        self,
        spec: DesignSpec,
        created_objects: list[str],
        priority_issue: str,
        geometry_issues: list[dict[str, Any]],
        preview_image_path: str,
    ) -> list[dict[str, Any]]:
        """Rule-based fallback repair plan."""
        tool_calls: list[dict[str, Any]] = []

        if priority_issue == "geometry":
            for obj in created_objects:
                # Always recalculate normals
                tool_calls.append({
                    "tool": "edit_mesh",
                    "parameters": {"object_name": obj, "operation": "recalculate_normals"},
                })
                # Check if any issue mentions triangle budget
                if any("triangle" in str(iss).lower() or "budget" in str(iss).lower() for iss in geometry_issues):
                    tool_calls.append({
                        "tool": "add_modifier",
                        "parameters": {
                            "object_name": obj,
                            "modifier_type": "DECIMATE",
                            "modifier_name": "RepairDecimate",
                            "properties": {"ratio": 0.75},
                        },
                    })
                    tool_calls.append({
                        "tool": "apply_modifier",
                        "parameters": {"object_name": obj, "modifier_name": "RepairDecimate"},
                    })
        else:
            # Visual repair: boost studio lighting and re-render
            tool_calls.append({
                "tool": "setup_studio_lighting",
                "parameters": {"key_energy": 1600.0, "fill_energy": 600.0, "rim_energy": 1000.0},
            })
            tool_calls.append({
                "tool": "render_preview",
                "parameters": {
                    "output_path": preview_image_path,
                    "resolution_x": 1024,
                    "resolution_y": 1024,
                    "samples": 96,
                },
            })

        return tool_calls

    async def _execute_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        priority_issue: str,
        preview_image_path: str,
        geometry_repair_count: int,
        visual_revision_count: int,
    ) -> dict[str, Any]:
        """Execute a list of MCP tool calls and return updated state."""
        ops_executed = 0
        new_preview = preview_image_path

        for call in tool_calls:
            tool_name = call.get("tool", "")
            params = call.get("parameters", {})
            try:
                result = await self.mcp_server.call_tool(tool_name, params)
                if result.get("success", False):
                    ops_executed += 1
                    logger.info("  Repair op OK: %s", tool_name)
                    if tool_name == "render_preview":
                        new_preview = params.get("output_path", preview_image_path)
                else:
                    logger.warning("  Repair op FAILED: %s — %s", tool_name, result.get("error", ""))
            except Exception as exc:
                logger.warning("  Repair op exception: %s — %s", tool_name, exc)

        # Increment the appropriate counter
        new_geo_count = geometry_repair_count + (1 if priority_issue == "geometry" else 0)
        new_vis_count = visual_revision_count + (1 if priority_issue == "visual" else 0)

        logger.info(
            "RepairAgent done — ops_executed: %d | geo_repairs: %d | vis_revisions: %d",
            ops_executed,
            new_geo_count,
            new_vis_count,
        )

        return {
            "success": ops_executed > 0,
            "ops_executed": ops_executed,
            "new_preview_image_path": new_preview,
            "geometry_repair_count": new_geo_count,
            "visual_revision_count": new_vis_count,
        }
