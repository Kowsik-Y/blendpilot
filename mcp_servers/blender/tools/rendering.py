"""
BlendPilot — Rendering MCP Tools

Tools for framing preview cameras, setting up 3-point studio lighting, and rendering preview images.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from services.blender_client import BlenderClient


class SetupCameraInput(BaseModel):
    """Input parameters for setting up the preview camera."""
    target_object: str | None = Field(
        default=None, description="Object to focus the camera on")
    distance: float = Field(
        default=3.5, gt=0, description="Camera distance multiplier")
    focal_length: float = Field(
        default=50.0, gt=0, description="Lens focal length in mm")


class SetupLightingInput(BaseModel):
    """Input parameters for studio 3-point lighting setup."""
    key_energy: float = Field(default=1000.0, ge=0,
                              description="Key light power in Watts")
    fill_energy: float = Field(
        default=400.0, ge=0, description="Fill light power in Watts")
    rim_energy: float = Field(
        default=600.0, ge=0, description="Rim light power in Watts")


class RenderPreviewInput(BaseModel):
    """Input parameters for rendering a preview image."""
    output_path: str = Field(...,
                             description="File path for the rendered image (.png/.jpg)")
    resolution_x: int = Field(
        default=1024, gt=0, description="Image width in pixels")
    resolution_y: int = Field(
        default=1024, gt=0, description="Image height in pixels")
    samples: int = Field(default=64, gt=0, description="Render sample count")


async def setup_preview_camera(client: BlenderClient, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Position a preview camera oriented toward the asset."""
    validated = SetupCameraInput.model_validate(params or {})
    response = await client.execute("setup_preview_camera", validated.model_dump())
    return {
        "success": response.success,
        "camera_name": response.result.get("camera_name") if response.result else "PreviewCamera",
        "result": response.result,
        "error": response.error,
    }


async def setup_studio_lighting(client: BlenderClient, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a balanced 3-point studio lighting rig (Key, Fill, and Rim lights) for asset presentation."""
    validated = SetupLightingInput.model_validate(params or {})
    response = await client.execute("setup_studio_lighting", validated.model_dump())
    return {
        "success": response.success,
        "lights": response.result.get("lights", []) if response.result else [],
        "result": response.result,
        "error": response.error,
    }


async def render_preview(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Render a high-resolution preview image of the asset to disk for visual QA and human review."""
    validated = RenderPreviewInput.model_validate(params)
    response = await client.render_preview(
        output_path=validated.output_path,
        resolution_x=validated.resolution_x,
        resolution_y=validated.resolution_y,
    )
    return {
        "success": response.success,
        "output_path": validated.output_path,
        "result": response.result,
        "error": response.error,
    }
