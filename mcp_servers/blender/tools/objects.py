"""
BlendPilot AI — Object MCP Tools

Tools for creating primitives, transforming, duplicating, and deleting objects in Blender.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from services.blender_client import BlenderClient


class CreatePrimitiveInput(BaseModel):
    """Input parameters for creating a 3D primitive."""
    primitive_type: str = Field(
        ...,
        description="Type of primitive: 'cube', 'cylinder', 'uv_sphere', 'ico_sphere', 'plane', 'cone', 'torus'",
    )
    name: str = Field(..., description="Unique name for the created object")
    dimensions: list[float] = Field(
        default_factory=lambda: [1.0, 1.0, 1.0],
        description="[width (X), depth (Y), height (Z)] in Blender units / meters",
    )
    location: list[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0],
        description="[X, Y, Z] world position",
    )
    rotation: list[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0],
        description="[X, Y, Z] Euler rotation in radians",
    )


class SetTransformInput(BaseModel):
    """Input parameters for setting object transforms."""
    name: str = Field(..., description="Name of the target object")
    location: list[float] | None = Field(default=None, description="[X, Y, Z] world position")
    rotation: list[float] | None = Field(default=None, description="[X, Y, Z] Euler rotation in radians")
    scale: list[float] | None = Field(default=None, description="[X, Y, Z] scale multipliers")


class DuplicateObjectInput(BaseModel):
    """Input parameters for duplicating an object."""
    name: str = Field(..., description="Source object name")
    new_name: str | None = Field(default=None, description="Name for the duplicate object")
    offset: list[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0],
        description="Position offset relative to the source object",
    )


class DeleteObjectInput(BaseModel):
    """Input parameters for deleting an object."""
    name: str = Field(..., description="Name of the object to delete")


async def create_primitive(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Create a basic geometric primitive (cube, cylinder, sphere, plane) in Blender with specified dimensions and position."""
    validated = CreatePrimitiveInput.model_validate(params)
    response = await client.create_primitive(
        primitive_type=validated.primitive_type,
        name=validated.name,
        dimensions=validated.dimensions,
        location=validated.location,
        rotation=validated.rotation,
    )
    return {
        "success": response.success,
        "object_name": validated.name,
        "result": response.result,
        "error": response.error,
    }


async def set_transform(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Update location, rotation, or scale transforms of an existing object."""
    validated = SetTransformInput.model_validate(params)
    payload: dict[str, Any] = {"name": validated.name}
    if validated.location is not None:
        payload["location"] = validated.location
    if validated.rotation is not None:
        payload["rotation"] = validated.rotation
    if validated.scale is not None:
        payload["scale"] = validated.scale

    response = await client.set_transform(**payload)
    return {
        "success": response.success,
        "object_name": validated.name,
        "result": response.result,
        "error": response.error,
    }


async def duplicate_object(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Duplicate an existing object with optional name and location offset."""
    validated = DuplicateObjectInput.model_validate(params)
    response = await client.duplicate_object(
        name=validated.name,
        new_name=validated.new_name,
        offset=validated.offset,
    )
    return {
        "success": response.success,
        "source_object": validated.name,
        "new_object": response.result.get("name") if response.result else None,
        "result": response.result,
        "error": response.error,
    }


async def delete_object(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Delete an object and its mesh data from the scene."""
    validated = DeleteObjectInput.model_validate(params)
    response = await client.delete_object(name=validated.name)
    return {
        "success": response.success,
        "deleted_object": validated.name,
        "error": response.error,
    }
