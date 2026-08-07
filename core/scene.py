"""
BlendPilot AI — Scene Inspection

Functions for reading and summarizing the current Blender scene state.
These produce structured data for the Scene Understanding workflow.

Runs inside Blender's Python environment.
"""

from __future__ import annotations

import logging
from typing import Any

import bpy  # type: ignore[import-not-found]

logger = logging.getLogger("blendpilot.core.scene")


def get_scene_summary() -> dict[str, Any]:
    """Get a structured summary of the current Blender scene.

    Returns:
        Dict containing:
        - blend_file: Path to the current .blend file.
        - object_count: Total number of objects.
        - objects: List of object info dicts (name, type, location, etc.).
        - collections: List of collection names.
        - has_camera: Whether a camera exists.
        - has_lights: Whether lights exist.
        - active_object: Name of the active object, or None.
        - render_engine: Current render engine name.
    """
    scene = bpy.context.scene
    objects_info = []

    for obj in scene.objects:
        obj_info: dict[str, Any] = {
            "name": obj.name,
            "type": obj.type,
            "location": tuple(obj.location),
            "rotation": tuple(obj.rotation_euler),
            "scale": tuple(obj.scale),
            "dimensions": tuple(obj.dimensions),
            "parent": obj.parent.name if obj.parent else None,
            "visible": obj.visible_get(),
        }

        # Add modifier info
        if obj.modifiers:
            obj_info["modifiers"] = [
                {"name": m.name, "type": m.type, "show_viewport": m.show_viewport}
                for m in obj.modifiers
            ]

        # Add material info
        if obj.material_slots:
            obj_info["materials"] = [
                {
                    "slot_index": i,
                    "material_name": slot.material.name if slot.material else None,
                }
                for i, slot in enumerate(obj.material_slots)
            ]

        objects_info.append(obj_info)

    # Gather collections
    collections = [col.name for col in bpy.data.collections]

    # Check for cameras and lights
    has_camera = any(obj.type == "CAMERA" for obj in scene.objects)
    has_lights = any(obj.type == "LIGHT" for obj in scene.objects)

    active = bpy.context.view_layer.objects.active
    active_name = active.name if active else None

    summary = {
        "blend_file": bpy.data.filepath or "(unsaved)",
        "object_count": len(scene.objects),
        "objects": objects_info,
        "collections": collections,
        "has_camera": has_camera,
        "has_lights": has_lights,
        "active_object": active_name,
        "frame_current": scene.frame_current,
        "render_engine": scene.render.engine,
    }

    logger.info(
        "Scene summary: %d objects, camera=%s, lights=%s",
        len(scene.objects), has_camera, has_lights,
    )
    return summary


def get_object_details(name: str) -> dict[str, Any]:
    """Get detailed information about a specific object.

    Args:
        name: Name of the Blender object.

    Returns:
        Dict with complete object details.

    Raises:
        ValueError: If the object is not found.
    """
    if not name or not name.strip():
        raise ValueError("Object name cannot be empty.")

    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object '{name}' not found in scene.")

    details: dict[str, Any] = {
        "name": obj.name,
        "type": obj.type,
        "location": tuple(obj.location),
        "rotation_euler": tuple(obj.rotation_euler),
        "scale": tuple(obj.scale),
        "dimensions": tuple(obj.dimensions),
        "parent": obj.parent.name if obj.parent else None,
        "visible": obj.visible_get(),
        "modifiers": [],
        "materials": [],
        "constraints": [],
    }

    # Collection membership
    details["collections"] = [col.name for col in obj.users_collection]

    # Modifiers
    for mod in obj.modifiers:
        mod_info = {
            "name": mod.name,
            "type": mod.type,
            "show_viewport": mod.show_viewport,
            "show_render": mod.show_render,
        }
        details["modifiers"].append(mod_info)

    # Materials
    for i, slot in enumerate(obj.material_slots):
        mat_info = {
            "slot_index": i,
            "material_name": slot.material.name if slot.material else None,
        }
        details["materials"].append(mat_info)

    # Mesh-specific data
    if obj.type == "MESH" and obj.data:
        mesh = obj.data
        details["mesh"] = {
            "vertex_count": len(mesh.vertices),
            "edge_count": len(mesh.edges),
            "polygon_count": len(mesh.polygons),
            "has_uv": len(mesh.uv_layers) > 0,
            "uv_layer_count": len(mesh.uv_layers),
        }

    logger.info("Retrieved details for object '%s' (type=%s)", name, obj.type)
    return details


def get_mesh_statistics(name: str) -> dict[str, Any]:
    """Get mesh statistics for an object (vertex/edge/face/triangle counts).

    Uses bmesh to compute an accurate triangle count via triangulation.

    Args:
        name: Name of the mesh object.

    Returns:
        Dict with mesh statistics.

    Raises:
        ValueError: If object not found or not a mesh.
    """
    import bmesh  # type: ignore[import-not-found]

    if not name or not name.strip():
        raise ValueError("Object name cannot be empty.")

    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object '{name}' not found in scene.")

    if obj.type != "MESH":
        raise ValueError(
            f"Object '{name}' is type '{obj.type}', not MESH. "
            "Mesh statistics are only available for mesh objects."
        )

    mesh = obj.data

    # Use bmesh to get accurate triangle count
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()

    triangle_count = sum(len(f.verts) - 2 for f in bm.faces)
    has_ngons = any(len(f.verts) > 4 for f in bm.faces)

    stats = {
        "object_name": obj.name,
        "vertex_count": len(mesh.vertices),
        "edge_count": len(mesh.edges),
        "face_count": len(mesh.polygons),
        "triangle_count": triangle_count,
        "has_ngons": has_ngons,
        "dimensions": tuple(obj.dimensions),
        "bounding_box_volume": obj.dimensions.x * obj.dimensions.y * obj.dimensions.z,
        "has_uv": len(mesh.uv_layers) > 0,
    }

    bm.free()

    logger.info(
        "Mesh stats for '%s': %d verts, %d faces, %d tris",
        name, stats["vertex_count"], stats["face_count"], stats["triangle_count"],
    )
    return stats
