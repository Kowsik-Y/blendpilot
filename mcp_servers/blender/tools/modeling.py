"""
BlendPilot AI — Modeling MCP Tools

Tools for adding/applying modifiers and executing mesh operations in Blender.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from services.blender_client import BlenderClient


class AddModifierInput(BaseModel):
    """Input parameters for adding a modifier."""
    object_name: str = Field(..., description="Target object name")
    modifier_type: str = Field(
        ...,
        description="Type of modifier: 'BEVEL', 'SUBSURF', 'SOLIDIFY', 'MIRROR', 'BOOLEAN', 'EDGE_SPLIT', 'DECIMATE'",
    )
    modifier_name: str | None = Field(default=None, description="Optional custom name for the modifier")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Modifier-specific properties (e.g. width=0.05, segments=3, thickness=0.02)",
    )


class ApplyModifierInput(BaseModel):
    """Input parameters for applying a modifier."""
    object_name: str = Field(..., description="Target object name")
    modifier_name: str = Field(..., description="Name of the modifier to apply")


class EditMeshInput(BaseModel):
    """Input parameters for mesh editing operations."""
    object_name: str = Field(..., description="Target object name")
    operation: str = Field(..., description="Operation: 'extrude_face', 'inset_face', 'bevel_edges', 'subdivide', 'recalculate_normals'")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Operation specific parameters")


async def add_modifier(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Add a modifier (such as Bevel, Solidify, Mirror, Subsurf) to a mesh object with configured properties."""
    validated = AddModifierInput.model_validate(params)
    response = await client.add_modifier(
        object_name=validated.object_name,
        modifier_type=validated.modifier_type,
        modifier_name=validated.modifier_name,
        properties=validated.properties,
    )
    return {
        "success": response.success,
        "object_name": validated.object_name,
        "modifier": response.result,
        "error": response.error,
    }


async def apply_modifier(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Bake and apply a modifier into the underlying mesh geometry."""
    validated = ApplyModifierInput.model_validate(params)
    response = await client.apply_modifier(
        object_name=validated.object_name,
        modifier_name=validated.modifier_name,
    )
    return {
        "success": response.success,
        "object_name": validated.object_name,
        "modifier_name": validated.modifier_name,
        "error": response.error,
    }


async def edit_mesh(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Execute a low-level mesh operation (e.g. recalculate normals, subdivide, bevel)."""
    validated = EditMeshInput.model_validate(params)
    response = await client.execute("edit_mesh", validated.model_dump())
    return {
        "success": response.success,
        "object_name": validated.object_name,
        "operation": validated.operation,
        "result": response.result,
        "error": response.error,
    }
