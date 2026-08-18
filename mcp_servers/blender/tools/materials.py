"""
BlendPilot — Material MCP Tools

Tools for creating Principled BSDF / PBR materials and assigning them to Blender objects.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from services.blender_client import BlenderClient


class CreateMaterialInput(BaseModel):
    """Input parameters for creating a PBR material."""
    name: str = Field(..., description="Unique name for the material")
    base_color: list[float] = Field(
        default_factory=lambda: [0.8, 0.8, 0.8, 1.0],
        description="RGBA color values [0.0 - 1.0]",
    )
    metallic: float = Field(default=0.0, ge=0.0, le=1.0,
                            description="Metallic reflection value")
    roughness: float = Field(default=0.5, ge=0.0, le=1.0,
                             description="Surface roughness value")
    emission_color: list[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0, 1.0],
        description="RGBA emission color values [0.0 - 1.0]",
    )
    emission_strength: float = Field(
        default=0.0, ge=0.0, description="Emission glow strength multiplier")


class AssignMaterialInput(BaseModel):
    """Input parameters for assigning a material to an object."""
    object_name: str = Field(..., description="Target object name")
    material_name: str = Field(...,
                               description="Name of the material to assign")
    slot_index: int = Field(default=0, ge=0, description="Material slot index")


async def create_material(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Create a Principled BSDF material with custom base color, metallic, roughness, and emissive properties."""
    validated = CreateMaterialInput.model_validate(params)
    response = await client.create_material(
        name=validated.name,
        base_color=validated.base_color,
        metallic=validated.metallic,
        roughness=validated.roughness,
        emission_color=validated.emission_color,
        emission_strength=validated.emission_strength,
    )
    return {
        "success": response.success,
        "material_name": validated.name,
        "result": response.result,
        "error": response.error,
    }


async def assign_material(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Assign an existing material to a target mesh object."""
    validated = AssignMaterialInput.model_validate(params)
    response = await client.assign_material(
        object_name=validated.object_name,
        material_name=validated.material_name,
        slot_index=validated.slot_index,
    )
    return {
        "success": response.success,
        "object_name": validated.object_name,
        "material_name": validated.material_name,
        "error": response.error,
    }
