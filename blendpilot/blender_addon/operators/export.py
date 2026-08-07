"""
BlendPilot AI — Export Operators

Bridge handlers for project saving, checkpoints, and asset export.
Wraps core/project.py.
"""

from __future__ import annotations

import logging
from typing import Any

from blender_addon.operators import register_command

logger = logging.getLogger("blendpilot.addon.operators.export")


def handle_save_checkpoint(params: dict[str, Any]) -> dict[str, Any]:
    """Handle save_checkpoint command."""
    from core.project import save_checkpoint

    return save_checkpoint(
        path=params["path"],
        copy=params.get("copy", True),
    )


def handle_restore_checkpoint(params: dict[str, Any]) -> dict[str, Any]:
    """Handle restore_checkpoint command."""
    from core.project import restore_checkpoint

    return restore_checkpoint(path=params["path"])


def handle_save_project(params: dict[str, Any]) -> dict[str, Any]:
    """Handle save_project command."""
    from core.project import save_project

    return save_project(path=params["path"])


def handle_export_asset(params: dict[str, Any]) -> dict[str, Any]:
    """Handle export_asset command."""
    from core.project import export_asset

    return export_asset(
        object_names=params["object_names"],
        export_format=params.get("export_format", "FBX"),
        output_path=params["output_path"],
        apply_modifiers=params.get("apply_modifiers", True),
    )


def register() -> None:
    """Register all export command handlers."""
    register_command("save_checkpoint", handle_save_checkpoint)
    register_command("restore_checkpoint", handle_restore_checkpoint)
    register_command("save_project", handle_save_project)
    register_command("export_asset", handle_export_asset)
    logger.debug("Export operators registered.")
