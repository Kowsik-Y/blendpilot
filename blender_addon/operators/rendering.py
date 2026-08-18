"""
BlendPilot — Rendering Operators

Bridge handlers for camera, lighting, and preview rendering.
Wraps core/rendering.py.
"""

from __future__ import annotations

import logging
from typing import Any

from blender_addon.operators import register_command

logger = logging.getLogger("blendpilot.addon.operators.rendering")


def handle_setup_preview_camera(params: dict[str, Any]) -> dict[str, Any]:
    """Handle setup_preview_camera command."""
    from core.rendering import setup_preview_camera

    target = tuple(params.get("target", (0.0, 0.0, 0.0)))

    return setup_preview_camera(
        target=target,
        distance=params.get("distance", 5.0),
        elevation_angle=params.get("elevation_angle", 30.0),
        azimuth_angle=params.get("azimuth_angle", 45.0),
        camera_name=params.get("camera_name", "PreviewCamera"),
    )


def handle_setup_studio_lighting(params: dict[str, Any]) -> dict[str, Any]:
    """Handle setup_studio_lighting command."""
    from core.rendering import setup_studio_lighting

    target = tuple(params.get("target", (0.0, 0.0, 0.0)))

    return setup_studio_lighting(
        target=target,
        key_energy=params.get("key_energy", 300.0),
        fill_energy=params.get("fill_energy", 100.0),
        rim_energy=params.get("rim_energy", 200.0),
    )


def handle_render_preview(params: dict[str, Any]) -> dict[str, Any]:
    """Handle render_preview command."""
    from core.rendering import render_preview

    return render_preview(
        output_path=params["output_path"],
        resolution_x=params.get("resolution_x", 1920),
        resolution_y=params.get("resolution_y", 1080),
        samples=params.get("samples", 64),
        engine=params.get("engine", "BLENDER_EEVEE_NEXT"),
        transparent=params.get("transparent", False),
    )


def handle_get_scene_summary(params: dict[str, Any]) -> dict[str, Any]:
    """Handle get_scene_summary command."""
    from core.scene import get_scene_summary

    return get_scene_summary()


def handle_get_object_details(params: dict[str, Any]) -> dict[str, Any]:
    """Handle get_object_details command."""
    from core.scene import get_object_details

    return get_object_details(name=params["name"])


def handle_get_mesh_statistics(params: dict[str, Any]) -> dict[str, Any]:
    """Handle get_mesh_statistics command."""
    from core.scene import get_mesh_statistics

    return get_mesh_statistics(name=params["name"])


def register() -> None:
    """Register all rendering and scene command handlers."""
    register_command("setup_preview_camera", handle_setup_preview_camera)
    register_command("setup_studio_lighting", handle_setup_studio_lighting)
    register_command("render_preview", handle_render_preview)
    register_command("get_scene_summary", handle_get_scene_summary)
    register_command("get_object_details", handle_get_object_details)
    register_command("get_mesh_statistics", handle_get_mesh_statistics)
    logger.debug("Rendering operators registered.")
