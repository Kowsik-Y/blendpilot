"""
BlendPilot AI — Object Operators

Bridge handlers for object creation, transform, duplication, and deletion.
Wraps core/objects.py with parameter validation for bridge commands.
"""

from __future__ import annotations

import logging
from typing import Any

from blender_addon.operators import register_command

logger = logging.getLogger("blendpilot.addon.operators.objects")


def handle_create_primitive(params: dict[str, Any]) -> dict[str, Any]:
    """Handle create_primitive command."""
    from core.objects import create_primitive

    # Convert list params to tuples (JSON sends arrays)
    dimensions = tuple(params["dimensions"]) if "dimensions" in params and params["dimensions"] else None
    location = tuple(params.get("location", (0.0, 0.0, 0.0)))
    rotation = tuple(params.get("rotation", (0.0, 0.0, 0.0)))

    return create_primitive(
        primitive_type=params["primitive_type"],
        name=params["name"],
        dimensions=dimensions,
        location=location,
        rotation=rotation,
    )


def handle_set_transform(params: dict[str, Any]) -> dict[str, Any]:
    """Handle set_transform command."""
    from core.objects import set_transform

    location = tuple(params["location"]) if "location" in params else None
    rotation = tuple(params["rotation"]) if "rotation" in params else None
    scale = tuple(params["scale"]) if "scale" in params else None

    return set_transform(
        name=params["name"],
        location=location,
        rotation=rotation,
        scale=scale,
    )


def handle_duplicate_object(params: dict[str, Any]) -> dict[str, Any]:
    """Handle duplicate_object command."""
    from core.objects import duplicate_object

    offset = tuple(params.get("offset", (0.0, 0.0, 0.0)))

    return duplicate_object(
        name=params["name"],
        new_name=params.get("new_name"),
        offset=offset,
    )


def handle_delete_object(params: dict[str, Any]) -> dict[str, Any]:
    """Handle delete_object command."""
    from core.objects import delete_object

    return delete_object(name=params["name"])


def register() -> None:
    """Register all object command handlers."""
    register_command("create_primitive", handle_create_primitive)
    register_command("set_transform", handle_set_transform)
    register_command("duplicate_object", handle_duplicate_object)
    register_command("delete_object", handle_delete_object)
    logger.debug("Object operators registered.")
