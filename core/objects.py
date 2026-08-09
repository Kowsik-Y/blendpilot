"""
BlendPilot AI — Object Creation & Manipulation

Functions for creating Blender primitives, setting transforms,
duplicating, and deleting objects.

Runs inside Blender's Python environment.
"""

from __future__ import annotations

import logging
from typing import Any

import bpy  # type: ignore[import-not-found]

logger = logging.getLogger("blendpilot.core.objects")

# Supported primitive types and their bpy creation operators
PRIMITIVE_TYPES: dict[str, str] = {
    "cube": "mesh.primitive_cube_add",
    "sphere": "mesh.primitive_uv_sphere_add",
    "cylinder": "mesh.primitive_cylinder_add",
    "plane": "mesh.primitive_plane_add",
    "cone": "mesh.primitive_cone_add",
    "torus": "mesh.primitive_torus_add",
    "ico_sphere": "mesh.primitive_ico_sphere_add",
}


def create_primitive(
    primitive_type: str,
    name: str,
    dimensions: tuple[float, float, float] | None = None,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> dict[str, Any]:
    """Create a Blender mesh primitive.

    Args:
        primitive_type: One of 'cube', 'sphere', 'cylinder', 'plane',
                       'cone', 'torus', 'ico_sphere'.
        name: Name for the new object.
        dimensions: Optional (width, depth, height) to set after creation.
                    If None, uses Blender defaults.
        location: World-space position (x, y, z).
        rotation: Euler rotation in radians (x, y, z).

    Returns:
        Dict with 'success', 'object_name', and 'message'.

    Raises:
        ValueError: If primitive_type is not supported or name is empty.
    """
    # --- Input validation ---
    if not name or not name.strip():
        raise ValueError("Object name cannot be empty.")

    ptype = primitive_type.lower().strip()
    if ptype not in PRIMITIVE_TYPES:
        raise ValueError(
            f"Unsupported primitive type '{primitive_type}'. "
            f"Must be one of: {', '.join(PRIMITIVE_TYPES.keys())}"
        )

    if dimensions is not None:
        if len(dimensions) != 3:
            raise ValueError("Dimensions must be a tuple of 3 floats (width, depth, height).")
        if any(d <= 0 for d in dimensions):
            raise ValueError("All dimensions must be positive values.")

    if len(location) != 3:
        raise ValueError("Location must be a tuple of 3 floats (x, y, z).")
    if len(rotation) != 3:
        raise ValueError("Rotation must be a tuple of 3 floats (x, y, z) in radians.")

    # --- Create the primitive ---
    logger.info("Creating %s primitive '%s' at %s", ptype, name, location)

    operator_path = PRIMITIVE_TYPES[ptype]
    # Navigate the operator path: e.g. "mesh.primitive_cube_add"
    parts = operator_path.split(".")
    op = getattr(bpy.ops, parts[0])
    op_func = getattr(op, parts[1])
    op_func(location=location, rotation=rotation)

    # Rename the newly created object
    obj = bpy.context.active_object
    if obj is None:
        return {
            "success": False,
            "object_name": None,
            "message": f"Failed to create {ptype}: no active object after creation.",
        }

    obj.name = name

    # Set dimensions if provided
    if dimensions is not None:
        obj.dimensions = dimensions
        logger.info("Set dimensions of '%s' to %s", name, dimensions)

    # Deselect all to clean up
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    logger.info("Successfully created '%s' (%s)", obj.name, ptype)
    return {
        "success": True,
        "object_name": obj.name,
        "message": f"Created {ptype} '{obj.name}' at {location}.",
    }


def set_transform(
    name: str,
    location: tuple[float, float, float] | None = None,
    rotation: tuple[float, float, float] | None = None,
    scale: tuple[float, float, float] | None = None,
) -> dict[str, Any]:
    """Set the transform (location, rotation, scale) of an existing object.

    Args:
        name: Name of the Blender object to modify.
        location: New world-space position, or None to keep current.
        rotation: New Euler rotation in radians, or None to keep current.
        scale: New scale factors, or None to keep current.

    Returns:
        Dict with 'success' and 'message'.

    Raises:
        ValueError: If name is empty or object not found.
    """
    if not name or not name.strip():
        raise ValueError("Object name cannot be empty.")

    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object '{name}' not found in scene.")

    changes = []

    if location is not None:
        if len(location) != 3:
            raise ValueError("Location must be a tuple of 3 floats.")
        obj.location = location
        changes.append(f"location={location}")

    if rotation is not None:
        if len(rotation) != 3:
            raise ValueError("Rotation must be a tuple of 3 floats (radians).")
        obj.rotation_euler = rotation
        changes.append(f"rotation={rotation}")

    if scale is not None:
        if len(scale) != 3:
            raise ValueError("Scale must be a tuple of 3 floats.")
        if any(s == 0 for s in scale):
            raise ValueError("Scale values cannot be zero.")
        obj.scale = scale
        changes.append(f"scale={scale}")

    if not changes:
        return {
            "success": True,
            "message": f"No transform changes specified for '{name}'.",
        }

    change_str = ", ".join(changes)
    logger.info("Set transform on '%s': %s", name, change_str)
    return {
        "success": True,
        "message": f"Updated transform on '{name}': {change_str}.",
    }


def duplicate_object(
    name: str,
    new_name: str | None = None,
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> dict[str, Any]:
    """Duplicate an existing object.

    Args:
        name: Name of the object to duplicate.
        new_name: Name for the duplicate. If None, Blender auto-generates.
        offset: Position offset from the original.

    Returns:
        Dict with 'success', 'object_name', and 'message'.

    Raises:
        ValueError: If the source object is not found.
    """
    if not name or not name.strip():
        raise ValueError("Object name cannot be empty.")

    src = bpy.data.objects.get(name)
    if src is None:
        raise ValueError(f"Source object '{name}' not found in scene.")

    # Select only the source object
    bpy.ops.object.select_all(action="DESELECT")
    src.select_set(True)
    bpy.context.view_layer.objects.active = src

    # Duplicate
    bpy.ops.object.duplicate(linked=False)
    dup = bpy.context.active_object

    if dup is None:
        return {
            "success": False,
            "object_name": None,
            "message": f"Failed to duplicate '{name}'.",
        }

    # Rename if requested
    if new_name:
        dup.name = new_name

    # Apply offset
    dup.location = (
        dup.location.x + offset[0],
        dup.location.y + offset[1],
        dup.location.z + offset[2],
    )

    logger.info("Duplicated '%s' → '%s' with offset %s", name, dup.name, offset)
    return {
        "success": True,
        "object_name": dup.name,
        "message": f"Duplicated '{name}' as '{dup.name}'.",
    }


def delete_object(name: str) -> dict[str, Any]:
    """Delete an object from the scene.

    Args:
        name: Name of the object to delete.

    Returns:
        Dict with 'success' and 'message'.

    Raises:
        ValueError: If the object is not found.
    """
    if not name or not name.strip():
        raise ValueError("Object name cannot be empty.")

    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object '{name}' not found in scene.")

    # Select the object and delete
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.delete(use_global=False)

    logger.info("Deleted object '%s'", name)
    return {
        "success": True,
        "message": f"Deleted object '{name}'.",
    }
