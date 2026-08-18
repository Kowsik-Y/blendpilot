"""
BlendPilot — Project MCP Tools

Tools for saving milestone checkpoints, rolling back states, saving .blend files, and exporting FBX/GLB.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from services.blender_client import BlenderClient


class SaveCheckpointInput(BaseModel):
    """Input parameters for saving an incremental checkpoint."""
    filepath: str = Field(...,
                          description="Destination file path for the .blend checkpoint")
    checkpoint_name: str | None = Field(
        default=None, description="Descriptive checkpoint label")


class RestoreCheckpointInput(BaseModel):
    """Input parameters for restoring a checkpoint."""
    filepath: str = Field(...,
                          description="Filepath of the .blend checkpoint to restore")


class SaveProjectInput(BaseModel):
    """Input parameters for saving the main project."""
    filepath: str = Field(..., description="Destination file path (.blend)")


class ExportAssetInput(BaseModel):
    """Input parameters for exporting a 3D asset."""
    object_names: list[str] = Field(...,
                                    description="Names of objects to include in the export")
    output_path: str = Field(...,
                             description="Destination file path (.fbx, .glb, .obj)")
    format: str = Field(
        default="FBX", description="Export format: 'FBX', 'GLB', 'OBJ'")
    apply_modifiers: bool = Field(
        default=True, description="Whether to apply active modifiers during export")


async def save_checkpoint(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Save an incremental .blend checkpoint for rollback safety."""
    validated = SaveCheckpointInput.model_validate(params)
    response = await client.save_checkpoint(filepath=validated.filepath)
    return {
        "success": response.success,
        "checkpoint_path": validated.filepath,
        "result": response.result,
        "error": response.error,
    }


async def restore_checkpoint(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Roll back the scene state to a previously saved .blend checkpoint."""
    validated = RestoreCheckpointInput.model_validate(params)
    response = await client.restore_checkpoint(filepath=validated.filepath)
    return {
        "success": response.success,
        "restored_path": validated.filepath,
        "result": response.result,
        "error": response.error,
    }


async def save_project(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Save the current working project state to disk as a .blend file."""
    validated = SaveProjectInput.model_validate(params)
    response = await client.save_project(filepath=validated.filepath)
    return {
        "success": response.success,
        "project_path": validated.filepath,
        "result": response.result,
        "error": response.error,
    }


async def export_asset(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Export selected objects to production game-engine formats (FBX, GLTF/GLB)."""
    validated = ExportAssetInput.model_validate(params)
    response = await client.export_asset(
        object_names=validated.object_names,
        output_path=validated.output_path,
        format=validated.format,
        apply_modifiers=validated.apply_modifiers,
    )
    return {
        "success": response.success,
        "export_path": validated.output_path,
        "format": validated.format,
        "result": response.result,
        "error": response.error,
    }
