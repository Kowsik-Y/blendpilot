"""
BlendPilot — Modifier Management

Functions for adding and applying Blender modifiers (bevel, solidify, etc.).

Runs inside Blender's Python environment.
"""

from __future__ import annotations

import logging
from typing import Any

import bpy  # type: ignore[import-not-found]

logger = logging.getLogger("blendpilot.core.modifiers")

# Supported modifier types mapped to Blender internal names
MODIFIER_TYPES: dict[str, str] = {
    "bevel": "BEVEL",
    "solidify": "SOLIDIFY",
    "subdivision": "SUBSURF",
    "mirror": "MIRROR",
    "array": "ARRAY",
    "boolean": "BOOLEAN",
    "decimate": "DECIMATE",
    "edge_split": "EDGE_SPLIT",
    "weighted_normal": "WEIGHTED_NORMAL",
}

# Default parameters for each modifier type
MODIFIER_DEFAULTS: dict[str, dict[str, Any]] = {
    "BEVEL": {
        "width": 0.02,
        "segments": 2,
        "limit_method": "ANGLE",
        "angle_limit": 0.523599,  # 30 degrees in radians
    },
    "SOLIDIFY": {
        "thickness": 0.05,
        "offset": -1.0,
    },
    "SUBSURF": {
        "levels": 1,
        "render_levels": 2,
    },
    "MIRROR": {
        "use_axis": (True, False, False),
    },
    "ARRAY": {
        "count": 2,
        "relative_offset_displace": (1.0, 0.0, 0.0),
    },
    "DECIMATE": {
        "ratio": 0.5,
    },
}


def add_modifier(
    object_name: str,
    modifier_type: str,
    modifier_name: str | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add a modifier to a Blender object.

    Args:
        object_name: Name of the target object.
        modifier_type: Type of modifier — one of: bevel, solidify, subdivision,
                      mirror, array, boolean, decimate, edge_split, weighted_normal.
        modifier_name: Display name for the modifier. Auto-generated if None.
        params: Optional dict of modifier-specific parameters to override defaults.

    Returns:
        Dict with 'success', 'modifier_name', and 'message'.

    Raises:
        ValueError: If object not found or modifier type not supported.
    """
    if not object_name or not object_name.strip():
        raise ValueError("Object name cannot be empty.")

    mtype = modifier_type.lower().strip()
    if mtype not in MODIFIER_TYPES:
        raise ValueError(
            f"Unsupported modifier type '{modifier_type}'. "
            f"Must be one of: {', '.join(MODIFIER_TYPES.keys())}"
        )

    obj = bpy.data.objects.get(object_name)
    if obj is None:
        raise ValueError(f"Object '{object_name}' not found in scene.")

    if obj.type != "MESH":
        raise ValueError(
            f"Object '{object_name}' is type '{obj.type}', not MESH. "
            "Modifiers can only be added to mesh objects."
        )

    blender_type = MODIFIER_TYPES[mtype]
    mod_name = modifier_name or f"{mtype.capitalize()}Modifier"

    # Add the modifier
    modifier = obj.modifiers.new(name=mod_name, type=blender_type)

    # Apply default parameters
    defaults = MODIFIER_DEFAULTS.get(blender_type, {})
    for key, value in defaults.items():
        if hasattr(modifier, key):
            try:
                setattr(modifier, key, value)
            except (TypeError, AttributeError) as e:
                logger.warning(
                    "Could not set default %s=%s: %s", key, value, e)

    # Apply user-specified parameters (override defaults)
    if params:
        for key, value in params.items():
            if hasattr(modifier, key):
                try:
                    setattr(modifier, key, value)
                except (TypeError, AttributeError) as e:
                    logger.warning(
                        "Could not set param %s=%s: %s", key, value, e)
            else:
                logger.warning(
                    "Modifier '%s' has no attribute '%s' — skipping.",
                    mod_name, key,
                )

    logger.info(
        "Added %s modifier '%s' to '%s'",
        blender_type, modifier.name, object_name,
    )
    return {
        "success": True,
        "modifier_name": modifier.name,
        "message": f"Added {blender_type} modifier '{modifier.name}' to '{object_name}'.",
    }


def apply_modifier(
    object_name: str,
    modifier_name: str,
) -> dict[str, Any]:
    """Apply (bake) a modifier to the mesh, making it permanent.

    Args:
        object_name: Name of the object with the modifier.
        modifier_name: Name of the modifier to apply.

    Returns:
        Dict with 'success' and 'message'.

    Raises:
        ValueError: If object or modifier not found.
    """
    if not object_name or not object_name.strip():
        raise ValueError("Object name cannot be empty.")
    if not modifier_name or not modifier_name.strip():
        raise ValueError("Modifier name cannot be empty.")

    obj = bpy.data.objects.get(object_name)
    if obj is None:
        raise ValueError(f"Object '{object_name}' not found in scene.")

    # Check modifier exists
    modifier = obj.modifiers.get(modifier_name)
    if modifier is None:
        available = [m.name for m in obj.modifiers]
        raise ValueError(
            f"Modifier '{modifier_name}' not found on '{object_name}'. "
            f"Available modifiers: {available}"
        )

    # Select the object and apply
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.modifier_apply(modifier=modifier_name)

    logger.info("Applied modifier '%s' on '%s'", modifier_name, object_name)
    return {
        "success": True,
        "message": f"Applied modifier '{modifier_name}' on '{object_name}'.",
    }
