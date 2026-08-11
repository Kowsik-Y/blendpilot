"""
BlendPilot AI — Scene MCP Tools

Tools for inspecting the active Blender scene and querying mesh statistics.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field
import os
import tempfile

from schemas.scene import ObjectInfo, SceneSummary, MeshStatistics
from services.blender_client import BlenderClient


class SceneSnapshotInput(BaseModel):
    """Input for creating a fast scene snapshot."""
    snapshot_name: str = Field(default="latest", description="Name of the snapshot")


class SceneRollbackInput(BaseModel):
    """Input for rolling back to a scene snapshot."""
    snapshot_name: str = Field(default="latest", description="Name of the snapshot to restore")


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


async def scene_snapshot(client: BlenderClient, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a fast memory snapshot of the current Blender scene before destructive operations."""
    validated = SceneSnapshotInput.model_validate(params or {})
    # Map fast snapshot to checkpoint API with a temporary file path
    filepath = os.path.join(tempfile.gettempdir(), f"blendpilot_snapshot_{validated.snapshot_name}.blend")
    response = await client.save_checkpoint(filepath=filepath)
    return {
        "success": response.success,
        "snapshot": validated.snapshot_name,
        "error": response.error
    }


async def scene_rollback(client: BlenderClient, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Roll back the active scene to a previously taken fast snapshot."""
    validated = SceneRollbackInput.model_validate(params or {})
    filepath = os.path.join(tempfile.gettempdir(), f"blendpilot_snapshot_{validated.snapshot_name}.blend")
    response = await client.restore_checkpoint(filepath=filepath)
    return {
        "success": response.success,
        "snapshot": validated.snapshot_name,
        "error": response.error
    }
