"""
BlendPilot AI — Scene MCP Tools

Tools for inspecting the active Blender scene and querying mesh statistics.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from schemas.scene import ObjectInfo, SceneSummary, MeshStatistics
from services.blender_client import BlenderClient


class GetSceneSummaryInput(BaseModel):
    """Input for getting the scene summary."""
    include_mesh_stats: bool = Field(default=True, description="Whether to include detailed vertex/face counts")


class GetObjectDetailsInput(BaseModel):
    """Input for getting object details."""
    name: str = Field(..., description="Name of the object to inspect")


class GetMeshStatisticsInput(BaseModel):
    """Input for getting mesh statistics."""
    name: str = Field(..., description="Name of the mesh object")


async def get_scene_summary(client: BlenderClient, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Inspect the active Blender scene and retrieve all objects, transforms, materials, lights, and camera."""
    response = await client.get_scene_summary()
    if not response.success or not response.result:
        return {
            "success": False,
            "error": response.error or "Failed to retrieve scene summary",
            "scene": SceneSummary().model_dump(),
        }
    return {
        "success": True,
        "scene": response.result,
    }


async def get_object_details(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Retrieve detailed transform, modifier, and material information for a specific object."""
    validated = GetObjectDetailsInput.model_validate(params)
    response = await client.get_object_details(name=validated.name)
    if not response.success or not response.result:
        return {
            "success": False,
            "error": response.error or f"Object '{validated.name}' not found",
            "object": None,
        }
    return {
        "success": True,
        "object": response.result,
    }


async def get_mesh_statistics(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Retrieve vertex, edge, polygon, and triangle counts for a specific mesh object."""
    validated = GetMeshStatisticsInput.model_validate(params)
    response = await client.get_mesh_statistics(name=validated.name)
    if not response.success or not response.result:
        return {
            "success": False,
            "error": response.error or f"Mesh stats unavailable for '{validated.name}'",
            "statistics": None,
        }
    return {
        "success": True,
        "statistics": response.result,
    }
