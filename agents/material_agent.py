"""
BlendPilot AI — Materials, Lighting, and Rendering Agent

Workflow 6: Creates PBR shaders, assigns materials to geometry, sets up studio lighting
and preview camera, and triggers render generation.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp_servers.blender.server import BlenderMCPServer
from schemas.design import DesignSpec

logger = logging.getLogger("blendpilot.agents.material")


class MaterialAgent:
    """Agent responsible for PBR materials, 3-point studio lighting, and preview rendering."""

    def __init__(self, mcp_server: BlenderMCPServer | None = None):
        self.mcp_server = mcp_server or BlenderMCPServer()

    async def execute(
        self,
        spec: DesignSpec,
        created_objects: list[str],
        output_image_path: str = "output/preview.png",
    ) -> dict[str, Any]:
        """Create PBR materials, assign to objects, set up lighting/camera, and render preview."""
        logger.info("Applying materials & lighting for %s (objects: %s)...", spec.asset_type, created_objects)

        materials_created: list[str] = []

        # 1. Generate & Assign PBR Materials based on spec
        if "dark_metal" in spec.materials or "metallic" in spec.style.lower() or "sci-fi" in spec.style.lower():
            # Main dark metal
            mat1 = f"Mat_{spec.asset_type}_DarkMetal"
            await self.mcp_server.call_tool("create_material", {
                "name": mat1,
                "base_color": [0.12, 0.13, 0.15, 1.0],
                "metallic": 0.85,
                "roughness": 0.35,
            })
            materials_created.append(mat1)

            # Emissive blue accent
            mat2 = f"Mat_{spec.asset_type}_EmissiveBlue"
            await self.mcp_server.call_tool("create_material", {
                "name": mat2,
                "base_color": [0.05, 0.4, 0.95, 1.0],
                "metallic": 0.1,
                "roughness": 0.2,
                "emission_color": [0.0, 0.5, 1.0, 1.0],
                "emission_strength": 5.0,
            })
            materials_created.append(mat2)

            # Assign to created objects
            if created_objects:
                await self.mcp_server.call_tool("assign_material", {
                    "object_name": created_objects[0],
                    "material_name": mat1,
                })
                if len(created_objects) > 1:
                    await self.mcp_server.call_tool("assign_material", {
                        "object_name": created_objects[1],
                        "material_name": mat2,
                    })
        elif "wood_grain" in spec.materials or "wood" in spec.asset_type.lower():
            mat_wood = f"Mat_{spec.asset_type}_Wood"
            await self.mcp_server.call_tool("create_material", {
                "name": mat_wood,
                "base_color": [0.4, 0.25, 0.15, 1.0],
                "metallic": 0.0,
                "roughness": 0.7,
            })
            materials_created.append(mat_wood)
            for obj in created_objects:
                await self.mcp_server.call_tool("assign_material", {
                    "object_name": obj,
                    "material_name": mat_wood,
                })
        else:
            # Default clean stylized PBR material
            mat_default = f"Mat_{spec.asset_type}_PBR"
            await self.mcp_server.call_tool("create_material", {
                "name": mat_default,
                "base_color": [0.75, 0.75, 0.78, 1.0],
                "metallic": 0.2,
                "roughness": 0.4,
            })
            materials_created.append(mat_default)
            for obj in created_objects:
                await self.mcp_server.call_tool("assign_material", {
                    "object_name": obj,
                    "material_name": mat_default,
                })

        # 2. Studio Lighting Setup
        await self.mcp_server.call_tool("setup_studio_lighting", {
            "key_energy": 1200.0,
            "fill_energy": 450.0,
            "rim_energy": 700.0,
        })

        # 3. Preview Camera Setup
        target = created_objects[0] if created_objects else None
        await self.mcp_server.call_tool("setup_preview_camera", {
            "target_object": target,
            "distance": 3.2,
            "focal_length": 50.0,
        })

        # 4. Render Preview
        render_res = await self.mcp_server.call_tool("render_preview", {
            "output_path": output_image_path,
            "resolution_x": 1024,
            "resolution_y": 1024,
            "samples": 64,
        })

        return {
            "success": True,
            "materials": materials_created,
            "preview_image_path": output_image_path,
            "render_result": render_res,
        }
