"""
BlendPilot AI — Project Management

Functions for saving checkpoints, restoring states, saving projects,
and exporting assets (FBX, GLB).

Runs inside Blender's Python environment.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import bpy  # type: ignore[import-not-found]

logger = logging.getLogger("blendpilot.core.project")


def save_checkpoint(
    path: str,
    copy: bool = True,
) -> dict[str, Any]:
    """Save a checkpoint of the current Blender project.

    Args:
        path: File path for the checkpoint (should end in .blend).
        copy: If True, saves a copy without changing the current file path.

    Returns:
        Dict with 'success', 'checkpoint_path', and 'message'.

    Raises:
        ValueError: If path is empty.
    """
    if not path or not path.strip():
        raise ValueError("Checkpoint path cannot be empty.")

    # Ensure .blend extension
    if not path.endswith(".blend"):
        path = path + ".blend"

    # Ensure directory exists
    out_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(out_dir, exist_ok=True)

    abs_path = os.path.abspath(path)

    if copy:
        bpy.ops.wm.save_as_mainfile(filepath=abs_path, copy=True)
    else:
        bpy.ops.wm.save_as_mainfile(filepath=abs_path)

    logger.info("Saved checkpoint: %s (copy=%s)", abs_path, copy)
    return {
        "success": True,
        "checkpoint_path": abs_path,
        "message": f"Checkpoint saved to '{abs_path}'.",
    }


def restore_checkpoint(path: str) -> dict[str, Any]:
    """Restore a previously saved checkpoint.

    WARNING: This will discard the current scene state.

    Args:
        path: Path to the .blend checkpoint file.

    Returns:
        Dict with 'success' and 'message'.

    Raises:
        ValueError: If path is empty.
        FileNotFoundError: If the checkpoint file doesn't exist.
    """
    if not path or not path.strip():
        raise ValueError("Checkpoint path cannot be empty.")

    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Checkpoint file not found: '{abs_path}'")

    bpy.ops.wm.open_mainfile(filepath=abs_path)

    logger.info("Restored checkpoint: %s", abs_path)
    return {
        "success": True,
        "message": f"Restored checkpoint from '{abs_path}'.",
    }


def save_project(path: str) -> dict[str, Any]:
    """Save the current project as the working .blend file.

    Args:
        path: File path for the project file.

    Returns:
        Dict with 'success', 'project_path', and 'message'.
    """
    if not path or not path.strip():
        raise ValueError("Project path cannot be empty.")

    if not path.endswith(".blend"):
        path = path + ".blend"

    out_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(out_dir, exist_ok=True)

    abs_path = os.path.abspath(path)
    bpy.ops.wm.save_as_mainfile(filepath=abs_path)

    logger.info("Saved project: %s", abs_path)
    return {
        "success": True,
        "project_path": abs_path,
        "message": f"Project saved to '{abs_path}'.",
    }


def export_asset(
    object_names: list[str],
    export_format: str = "FBX",
    output_path: str = "",
    apply_modifiers: bool = True,
) -> dict[str, Any]:
    """Export selected objects to FBX or GLB format.

    Args:
        object_names: List of object names to export.
        export_format: 'FBX' or 'GLB'.
        output_path: Output file path. Extension is added automatically if missing.
        apply_modifiers: Whether to apply modifiers during export.

    Returns:
        Dict with 'success', 'export_path', 'format', and 'message'.

    Raises:
        ValueError: If no objects specified, format unsupported, or objects not found.
    """
    if not object_names:
        raise ValueError("At least one object name must be specified for export.")

    export_format = export_format.upper().strip()
    if export_format not in ("FBX", "GLB", "GLTF"):
        raise ValueError(
            f"Unsupported export format '{export_format}'. Must be 'FBX' or 'GLB'."
        )

    if not output_path or not output_path.strip():
        raise ValueError("Output path cannot be empty.")

    # Validate all objects exist
    missing = [name for name in object_names if bpy.data.objects.get(name) is None]
    if missing:
        raise ValueError(f"Objects not found in scene: {missing}")

    # Add correct extension
    if export_format == "FBX" and not output_path.endswith(".fbx"):
        output_path = output_path + ".fbx"
    elif export_format in ("GLB", "GLTF") and not output_path.endswith((".glb", ".gltf")):
        output_path = output_path + ".glb"

    # Ensure output directory exists
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)

    abs_path = os.path.abspath(output_path)

    # Select only the specified objects
    bpy.ops.object.select_all(action="DESELECT")
    for name in object_names:
        obj = bpy.data.objects[name]
        obj.select_set(True)

    # Set the first object as active
    bpy.context.view_layer.objects.active = bpy.data.objects[object_names[0]]

    # Export
    if export_format == "FBX":
        bpy.ops.export_scene.fbx(
            filepath=abs_path,
            use_selection=True,
            apply_scale_options="FBX_SCALE_ALL",
            use_mesh_modifiers=apply_modifiers,
            mesh_smooth_type="FACE",
            path_mode="COPY",
            embed_textures=True,
        )
    else:
        bpy.ops.export_scene.gltf(
            filepath=abs_path,
            use_selection=True,
            export_format="GLB",
            export_apply=apply_modifiers,
        )

    logger.info("Exported %s → %s (%d objects)", export_format, abs_path, len(object_names))
    return {
        "success": True,
        "export_path": abs_path,
        "format": export_format,
        "exported_objects": object_names,
        "message": f"Exported {len(object_names)} object(s) as {export_format} to '{abs_path}'.",
    }
