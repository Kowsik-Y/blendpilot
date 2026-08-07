"""
BlendPilot AI — Material Operators

Bridge handlers for material creation and assignment.
Wraps core/materials.py.
"""

from __future__ import annotations

import logging
from typing import Any

from blender_addon.operators import register_command

logger = logging.getLogger("blendpilot.addon.operators.materials")


def handle_create_material(params: dict[str, Any]) -> dict[str, Any]:
    """Handle create_material command."""
    from core.materials import create_material

    base_color = tuple(params.get("base_color", (0.8, 0.8, 0.8, 1.0)))
    emission_color = tuple(params["emission_color"]) if "emission_color" in params else None

    return create_material(
        name=params["name"],
        base_color=base_color,
        metallic=params.get("metallic", 0.0),
        roughness=params.get("roughness", 0.5),
        emission_color=emission_color,
        emission_strength=params.get("emission_strength", 0.0),
    )


def handle_assign_material(params: dict[str, Any]) -> dict[str, Any]:
    """Handle assign_material command."""
    from core.materials import assign_material

    return assign_material(
        object_name=params["object_name"],
        material_name=params["material_name"],
    )


def register() -> None:
    """Register all material command handlers."""
    register_command("create_material", handle_create_material)
    register_command("assign_material", handle_assign_material)
    logger.debug("Material operators registered.")
