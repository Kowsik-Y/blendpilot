"""
BlendPilot AI — Modeling Operators

Bridge handlers for modifier management.
Wraps core/modifiers.py.
"""

from __future__ import annotations

import logging
from typing import Any

from blender_addon.operators import register_command

logger = logging.getLogger("blendpilot.addon.operators.modeling")


def handle_add_modifier(params: dict[str, Any]) -> dict[str, Any]:
    """Handle add_modifier command."""
    from core.modifiers import add_modifier

    return add_modifier(
        object_name=params["object_name"],
        modifier_type=params["modifier_type"],
        modifier_name=params.get("modifier_name"),
        params=params.get("params"),
    )


def handle_apply_modifier(params: dict[str, Any]) -> dict[str, Any]:
    """Handle apply_modifier command."""
    from core.modifiers import apply_modifier

    return apply_modifier(
        object_name=params["object_name"],
        modifier_name=params["modifier_name"],
    )


def register() -> None:
    """Register all modeling command handlers."""
    register_command("add_modifier", handle_add_modifier)
    register_command("apply_modifier", handle_apply_modifier)
    logger.debug("Modeling operators registered.")
