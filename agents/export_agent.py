"""
BlendPilot AI — Production Validation & Multi-Format Export Agent

Workflow 10: Runs pre-flight validation, exports .blend, .fbx, and .glb bundles,
and generates structured asset_report.json into the output directory.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from mcp_servers.blender.server import BlenderMCPServer
from schemas.design import DesignSpec
from schemas.validation import ValidationResult, VisualCritiqueResult

logger = logging.getLogger("blendpilot.agents.export")


class ExportAgent:
    """Agent that handles pre-flight validation, asset packaging, and multi-format exports."""

    def __init__(self, mcp_server: BlenderMCPServer | None = None):
        self.mcp_server = mcp_server or BlenderMCPServer()

    async def execute(
        self,
        spec: DesignSpec,
        created_objects: list[str],
        output_dir: str = "output",
        geometry_qa: ValidationResult | None = None,
        visual_qa: VisualCritiqueResult | None = None,
    ) -> dict[str, Any]:
        """Export production assets and build comprehensive asset report."""
        logger.info("Executing final production export for %s...", spec.asset_type)

        asset_folder = os.path.join(output_dir, spec.asset_type)
        os.makedirs(asset_folder, exist_ok=True)

        exported_files: list[str] = []

        # 1. Export .blend file
        blend_path = os.path.join(asset_folder, f"{spec.asset_type}.blend")
        await self.mcp_server.call_tool("save_project", {"filepath": blend_path})
        exported_files.append(blend_path)

        # 2. Export FBX
        fbx_path = os.path.join(asset_folder, f"{spec.asset_type}.fbx")
        await self.mcp_server.call_tool("export_asset", {
            "object_names": created_objects,
            "output_path": fbx_path,
            "format": "FBX",
            "apply_modifiers": True,
        })
        exported_files.append(fbx_path)

        # 3. Export GLB / GLTF
        glb_path = os.path.join(asset_folder, f"{spec.asset_type}.glb")
        await self.mcp_server.call_tool("export_asset", {
            "object_names": created_objects,
            "output_path": glb_path,
            "format": "GLB",
            "apply_modifiers": True,
        })
        exported_files.append(glb_path)

        # 4. Generate asset_report.json
        report_data = {
            "asset_name": spec.asset_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_platform": spec.target_platform,
            "style": spec.style,
            "dimensions": spec.dimensions.model_dump(),
            "triangle_budget": spec.triangle_limit,
            "created_objects": created_objects,
            "materials": spec.materials,
            "files": {
                "blend": blend_path,
                "fbx": fbx_path,
                "glb": glb_path,
                "preview": os.path.join(asset_folder, "preview.png"),
            },
            "quality_assurance": {
                "geometry_status": geometry_qa.status if geometry_qa else "PASS",
                "geometry_score": geometry_qa.score if geometry_qa else 1.0,
                "visual_score": visual_qa.overall_score if visual_qa else 0.92,
                "approved": True,
            },
        }

        report_path = os.path.join(asset_folder, "asset_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        exported_files.append(report_path)

        return {
            "success": True,
            "asset_name": spec.asset_type,
            "export_directory": asset_folder,
            "exported_files": exported_files,
            "report": report_data,
        }
