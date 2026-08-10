"""
BlendPilot AI — Materials, Lighting, and Rendering Agent

Workflow 6: Creates PBR shaders, assigns materials to geometry, sets up studio lighting
and preview camera, and triggers render generation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp_servers.blender.server import BlenderMCPServer
from schemas.design import DesignSpec
from services.llm import LLMService

logger = logging.getLogger("blendpilot.agents.material")


class MaterialAgent:
    """Agent responsible for PBR materials, 3-point studio lighting, and preview rendering."""

    def __init__(self, mcp_server: BlenderMCPServer | None = None, llm_service: LLMService | None = None):
        self.mcp_server = mcp_server or BlenderMCPServer()
        self.llm_service = llm_service or LLMService()

    async def execute(
        self,
        spec: DesignSpec,
        created_objects: list[str],
        output_image_path: str = "output/preview.png",
    ) -> dict[str, Any]:
        """Create PBR materials, assign to objects, set up lighting/camera, and render preview."""
        logger.info("Applying materials & lighting for %s (objects: %s)...", spec.asset_type, created_objects)

        materials_created: list[str] = []

        # 1. Generate PBR Materials via LLM based on spec
        prompt = f"""
Based on the following design specification, generate a list of 1 to 2 PBR materials.
Asset Type: {spec.asset_type}
Requested Materials: {spec.materials}
Style: {spec.style}

Return a JSON array of material objects. Each object should have:
- "name": string (e.g., "Mat_Metal")
- "base_color": list of 4 floats [R, G, B, A] (0.0 to 1.0)
- "metallic": float (0.0 to 1.0)
- "roughness": float (0.0 to 1.0)
- "emission_color": list of 4 floats [R, G, B, A] (optional)
- "emission_strength": float (optional)

Output ONLY valid JSON without any markdown formatting like ```json.
"""
        response = await self.llm_service.generate(prompt)
        
        generated_materials = []
        try:
            clean_res = response.strip()
            if clean_res.startswith("```json"):
                clean_res = clean_res[7:]
            if clean_res.startswith("```"):
                clean_res = clean_res[3:]
            if clean_res.endswith("```"):
                clean_res = clean_res[:-3]
            generated_materials = json.loads(clean_res.strip())
        except Exception as e:
            logger.error("Failed to parse LLM material generation: %s. Response was: %s", e, response)

        for i, mat_spec in enumerate(generated_materials):
            mat_name = mat_spec.get("name", f"Mat_{spec.asset_type}_{i}")
            mat_params = {
                "name": mat_name,
                "base_color": mat_spec.get("base_color", [0.8, 0.8, 0.8, 1.0]),
                "metallic": mat_spec.get("metallic", 0.0),
                "roughness": mat_spec.get("roughness", 0.5),
            }
            if "emission_color" in mat_spec:
                mat_params["emission_color"] = mat_spec["emission_color"]
            if "emission_strength" in mat_spec:
                mat_params["emission_strength"] = mat_spec["emission_strength"]
                
            await self.mcp_server.call_tool("create_material", mat_params)
            materials_created.append(mat_name)

        # Assign materials to created objects
        if materials_created and created_objects:
            for i, obj in enumerate(created_objects):
                mat_idx = min(i, len(materials_created) - 1)
                await self.mcp_server.call_tool("assign_material", {
                    "object_name": obj,
                    "material_name": materials_created[mat_idx],
                })


        # 2. Generate Camera & Lighting Setup via LLM
        setup_prompt = f"""
Generate studio lighting and preview camera parameters for a 3D asset.
Asset Type: {spec.asset_type}
Dimensions: {spec.dimensions.width}m x {spec.dimensions.depth}m x {spec.dimensions.height}m
Style: {spec.style}

Return a JSON object with:
- "key_energy": float (e.g. 1000.0 to 2000.0)
- "fill_energy": float
- "rim_energy": float
- "camera_distance": float (distance from object, based on dimensions)
- "focal_length": float (e.g. 35.0, 50.0, 85.0)

Output ONLY valid JSON without any markdown formatting.
"""
        setup_response = await self.llm_service.generate(setup_prompt)
        
        try:
            clean_res = setup_response.strip()
            if clean_res.startswith("```json"):
                clean_res = clean_res[7:]
            if clean_res.startswith("```"):
                clean_res = clean_res[3:]
            if clean_res.endswith("```"):
                clean_res = clean_res[:-3]
            cam_light_setup = json.loads(clean_res.strip())
        except Exception as e:
            logger.error("Failed to parse LLM lighting/camera generation: %s", e)
            raise RuntimeError(f"Failed to generate lighting/camera setup via LLM: {e}")

        # 3. Studio Lighting Setup
        await self.mcp_server.call_tool("setup_studio_lighting", {
            "key_energy": cam_light_setup["key_energy"],
            "fill_energy": cam_light_setup["fill_energy"],
            "rim_energy": cam_light_setup["rim_energy"],
        })

        # 4. Preview Camera Setup
        target = created_objects[0] if created_objects else None
        await self.mcp_server.call_tool("setup_preview_camera", {
            "target_object": target,
            "distance": cam_light_setup["camera_distance"],
            "focal_length": cam_light_setup["focal_length"],
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
