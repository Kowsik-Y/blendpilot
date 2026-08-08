"""
BlendPilot AI — Object Creation & Manipulation

Functions for creating Blender primitives, setting transforms,
duplicating, and deleting objects.

Design notes:
- Uses bpy.data API wherever possible instead of bpy.context.
- bpy.ops is only used for primitive creation and deletion (no direct data API).
- All functions return plain dicts with 'success' and 'message'.

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
    "uv_sphere": "mesh.primitive_uv_sphere_add",  # explicit alias
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
        primitive_type: One of 'cube', 'sphere', 'uv_sphere', 'cylinder',
                       'plane', 'cone', 'torus', 'ico_sphere'.
        name: Unique name for the new object. Must be non-empty.
        dimensions: Optional (width, depth, height) in metres. All values must
                    be positive. If None, Blender defaults are used.
        location: World-space position (x, y, z) in metres.
        rotation: Euler rotation in radians (rx, ry, rz).

    Returns:
        Dict with:
            - 'success' (bool)
            - 'object_name' (str | None)
            - 'message' (str)

    Raises:
        ValueError: If primitive_type is unsupported, name is empty,
                    dimensions/location/rotation have wrong length, or
                    any dimension value is non-positive.
    """
    # --- Input validation ---
    if not name or not name.strip():
        raise ValueError("Object name cannot be empty.")

    ptype = primitive_type.lower().strip()
    if ptype not in PRIMITIVE_TYPES:
        raise ValueError(
            f"Unsupported primitive type '{primitive_type}'. "
            f"Must be one of: {', '.join(sorted(set(PRIMITIVE_TYPES.keys())))}"
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

    # --- Create the primitive via bpy.ops ---
    logger.info("Creating %s primitive '%s' at %s", ptype, name, location)

    operator_path = PRIMITIVE_TYPES[ptype]
    parts = operator_path.split(".")
    op_func = getattr(getattr(bpy.ops, parts[0]), parts[1])
    op_func(location=location, rotation=rotation)

    # Retrieve the newly created object — prefer bpy.context.active_object
    obj = bpy.context.active_object
    if obj is None:
        return {
            "success": False,
            "object_name": None,
            "message": f"Failed to create {ptype}: no active object after creation.",
        }

    obj.name = name

    # Set dimensions if provided (via data API, no context needed)
    if dimensions is not None:
        obj.dimensions = dimensions
        logger.info("Set dimensions of '%s' to %s", name, dimensions)

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

    Uses bpy.data.objects directly — no bpy.context dependency.

    Args:
        name: Name of the Blender object to modify. Must be non-empty.
        location: New world-space position, or None to leave unchanged.
        rotation: New Euler rotation in radians, or None to leave unchanged.
        scale: New scale factors, or None to leave unchanged.
                All scale components must be non-zero.

    Returns:
        Dict with 'success' and 'message'.

    Raises:
        ValueError: If name is empty, object not found, any tuple has wrong
                    length, or a scale component is zero.
    """
    if not name or not name.strip():
        raise ValueError("Object name cannot be empty.")

    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object '{name}' not found in scene.")

    changes: list[str] = []

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
    """Duplicate an existing object using the data API where possible.

    The duplicate shares the same mesh data as the source (linked=False
    gives independent mesh), and an optional position offset is applied.

    Args:
        name: Name of the source object. Must be non-empty.
        new_name: Name for the duplicate. If None, Blender auto-generates.
        offset: XYZ position offset relative to the source object's location.

    Returns:
        Dict with:
            - 'success' (bool)
            - 'object_name' (str | None) — the duplicate's name
            - 'message' (str)

    Raises:
        ValueError: If name is empty or source object not found.
    """
    if not name or not name.strip():
        raise ValueError("Object name cannot be empty.")

    src = bpy.data.objects.get(name)
    if src is None:
        raise ValueError(f"Source object '{name}' not found in scene.")

    if len(offset) != 3:
        raise ValueError("Offset must be a tuple of 3 floats.")

    # Select only the source object, then duplicate via ops
    bpy.ops.object.select_all(action="DESELECT")
    src.select_set(True)
    bpy.context.view_layer.objects.active = src

    bpy.ops.object.duplicate(linked=False)
    dup = bpy.context.active_object

    if dup is None:
        return {
            "success": False,
            "object_name": None,
            "message": f"Failed to duplicate '{name}'.",
        }

    if new_name:
        dup.name = new_name

    # Apply position offset
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
    """Delete an object and its mesh data from the scene.

    Uses bpy.data.objects.remove() which does not require an active context
    selection state, and is more reliable than bpy.ops.object.delete().

    Args:
        name: Name of the object to delete. Must be non-empty.

    Returns:
        Dict with 'success' and 'message'.

    Raises:
        ValueError: If name is empty or the object is not found.
    """
    if not name or not name.strip():
        raise ValueError("Object name cannot be empty.")

    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object '{name}' not found in scene.")

    # Use data API: no context selection needed
    bpy.data.objects.remove(obj, do_unlink=True)

    logger.info("Deleted object '%s'", name)
    return {
        "success": True,
        "message": f"Deleted object '{name}'.",
    }
