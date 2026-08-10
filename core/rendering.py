"""
BlendPilot AI — Camera, Lighting & Rendering

Functions for setting up preview cameras, studio lighting,
and rendering preview images.

Runs inside Blender's Python environment.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any

import bpy  # type: ignore[import-not-found]

logger = logging.getLogger("blendpilot.core.rendering")


def setup_preview_camera(
    target: tuple[float, float, float] = (0.0, 0.0, 0.0),
    distance: float = 5.0,
    elevation_angle: float = 30.0,
    azimuth_angle: float = 45.0,
    camera_name: str = "PreviewCamera",
) -> dict[str, Any]:
    """Set up a camera aimed at a target point.

    The camera is positioned on a sphere around the target point,
    defined by distance, elevation, and azimuth angles.

    Args:
        target: Point the camera looks at (x, y, z).
        distance: Distance from the target in meters.
        elevation_angle: Vertical angle in degrees (0 = level, 90 = top-down).
        azimuth_angle: Horizontal angle in degrees (0 = front, 90 = right).
        camera_name: Name for the camera object.

    Returns:
        Dict with 'success', 'camera_name', and 'message'.
    """
    if distance <= 0:
        raise ValueError(f"Distance must be positive, got {distance}.")

    elev_rad = math.radians(elevation_angle)
    azim_rad = math.radians(azimuth_angle)

    # Calculate camera position on a sphere
    x = target[0] + distance * math.cos(elev_rad) * math.sin(azim_rad)
    y = target[1] - distance * math.cos(elev_rad) * math.cos(azim_rad)
    z = target[2] + distance * math.sin(elev_rad)

    # Check if camera already exists
    cam_obj = bpy.data.objects.get(camera_name)
    if cam_obj is not None and cam_obj.type == "CAMERA":
        # Reuse existing camera
        cam_obj.location = (x, y, z)
        logger.info("Updated existing camera '%s'.", camera_name)
    else:
        # Create new camera
        cam_data = bpy.data.cameras.new(name=camera_name)
        cam_data.lens = 50  # Standard focal length
        cam_data.clip_start = 0.1
        cam_data.clip_end = 1000.0

        cam_obj = bpy.data.objects.new(camera_name, cam_data)
        bpy.context.scene.collection.objects.link(cam_obj)
        cam_obj.location = (x, y, z)
        logger.info("Created new camera '%s'.", camera_name)

    # Point camera at target using a Track To constraint
    # Remove existing Track To constraints first
    for constraint in cam_obj.constraints:
        if constraint.type == "TRACK_TO":
            cam_obj.constraints.remove(constraint)

    # Use direct rotation calculation instead of constraint
    direction = (
        target[0] - x,
        target[1] - y,
        target[2] - z,
    )
    # Calculate rotation to look at target
    from mathutils import Vector  # type: ignore[import-not-found]

    dir_vec = Vector(direction)
    rot_quat = dir_vec.to_track_quat("-Z", "Y")
    cam_obj.rotation_euler = rot_quat.to_euler()

    # Set as active camera
    bpy.context.scene.camera = cam_obj

    logger.info(
        "Camera '%s' at (%.2f, %.2f, %.2f) looking at %s",
        camera_name, x, y, z, target,
    )
    return {
        "success": True,
        "camera_name": cam_obj.name,
        "message": f"Camera '{cam_obj.name}' positioned at distance {distance}m.",
    }


def setup_studio_lighting(
    target: tuple[float, float, float] = (0.0, 0.0, 0.0),
    key_energy: float = 300.0,
    fill_energy: float = 100.0,
    rim_energy: float = 200.0,
) -> dict[str, Any]:
    """Create a three-point studio lighting setup.

    Creates key, fill, and rim lights positioned around the target.

    Args:
        target: Center point that lights are aimed at.
        key_energy: Key light power in watts.
        fill_energy: Fill light power in watts.
        rim_energy: Rim/back light power in watts.

    Returns:
        Dict with 'success' and list of created light names.
    """
    if key_energy < 0 or fill_energy < 0 or rim_energy < 0:
        raise ValueError("Light energy values must be non-negative.")

    light_configs = [
        {
            "name": "KeyLight",
            "type": "AREA",
            "location": (3.0 + target[0], -2.0 + target[1], 4.0 + target[2]),
            "energy": key_energy,
            "size": 2.0,
        },
        {
            "name": "FillLight",
            "type": "AREA",
            "location": (-3.0 + target[0], -1.0 + target[1], 2.0 + target[2]),
            "energy": fill_energy,
            "size": 3.0,
        },
        {
            "name": "RimLight",
            "type": "AREA",
            "location": (0.0 + target[0], 3.0 + target[1], 3.0 + target[2]),
            "energy": rim_energy,
            "size": 1.5,
        },
    ]

    created_lights = []

    for config in light_configs:
        light_name = config["name"]

        # Remove existing light with the same name
        existing = bpy.data.objects.get(light_name)
        if existing is not None:
            bpy.data.objects.remove(existing, do_unlink=True)

        # Create light data
        light_data = bpy.data.lights.new(name=light_name, type=config["type"])
        light_data.energy = config["energy"]
        if config["type"] == "AREA":
            light_data.size = config["size"]

        # Create light object
        light_obj = bpy.data.objects.new(light_name, light_data)
        bpy.context.scene.collection.objects.link(light_obj)
        light_obj.location = config["location"]

        # Point light at target
        from mathutils import Vector  # type: ignore[import-not-found]

        direction = Vector((
            target[0] - config["location"][0],
            target[1] - config["location"][1],
            target[2] - config["location"][2],
        ))
        rot_quat = direction.to_track_quat("-Z", "Y")
        light_obj.rotation_euler = rot_quat.to_euler()

        created_lights.append(light_obj.name)
        logger.info("Created %s '%s' (%.0f W)", config["type"], light_obj.name, config["energy"])

    return {
        "success": True,
        "lights": created_lights,
        "message": f"Studio lighting setup complete: {', '.join(created_lights)}.",
    }


def render_preview(
    output_path: str,
    resolution_x: int = 1920,
    resolution_y: int = 1080,
    samples: int = 64,
    engine: str = "BLENDER_EEVEE_NEXT",
    transparent: bool = False,
) -> dict[str, Any]:
    """Render a preview image of the current scene.

    Args:
        output_path: File path for the rendered image (should end in .png).
        resolution_x: Horizontal resolution in pixels.
        resolution_y: Vertical resolution in pixels.
        samples: Number of render samples.
        engine: Render engine ('BLENDER_EEVEE_NEXT', 'CYCLES').
        transparent: If True, render with a transparent background.

    Returns:
        Dict with 'success', 'output_path', and 'message'.

    Raises:
        ValueError: If no camera is set or resolution is invalid.
    """
    if not output_path or not output_path.strip():
        raise ValueError("Output path cannot be empty.")
    if resolution_x <= 0 or resolution_y <= 0:
        raise ValueError("Resolution must be positive integers.")
    if samples <= 0:
        raise ValueError("Samples must be a positive integer.")

    scene = bpy.context.scene

    if scene.camera is None:
        raise ValueError("No active camera in the scene. Call setup_preview_camera() first.")

    # Ensure output directory exists
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)

    # Configure render settings
    try:
        scene.render.engine = engine
    except TypeError:
        # Fallback to standard EEVEE or CYCLES if engine name differs across versions
        if "EEVEE" in engine:
            scene.render.engine = "BLENDER_EEVEE"
        else:
            scene.render.engine = "CYCLES"

    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y
    scene.render.resolution_percentage = 100

    # Set samples
    if scene.render.engine == "CYCLES":
        if hasattr(scene, "cycles"):
            scene.cycles.samples = samples
    elif hasattr(scene, "eevee"):
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = samples
        elif hasattr(scene.eevee, "max_samples"):
            scene.eevee.max_samples = samples

    # Output format
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    scene.render.film_transparent = transparent

    # Set output path (must be absolute for Blender background rendering to work reliably)
    abs_path = os.path.abspath(output_path)
    scene.render.filepath = abs_path

    logger.info(
        "Rendering preview: %dx%d, %d samples, engine=%s → %s",
        resolution_x, resolution_y, samples, engine, output_path,
    )

    # Execute render
    bpy.ops.render.render(write_still=True)

    abs_path = os.path.abspath(output_path)
    logger.info("Render complete: %s", abs_path)

    return {
        "success": True,
        "output_path": abs_path,
        "message": f"Rendered preview ({resolution_x}×{resolution_y}) to '{abs_path}'.",
    }
