"""
BlendPilot AI — Stage 3: Scene Inspector

Deterministic scene inspection function that reads the actual Blender scene
and constructs a SceneState model.
"""

from __future__ import annotations

import logging
from typing import Any
import bpy  # type: ignore[import-not-found]

from schemas.scene_state import (
    SceneState,
    ObjectState,
    MaterialState,
    CameraState,
    LightState,
    ModifierState,
    Vec3,
)

logger = logging.getLogger("blendpilot.core.scene_inspector")


def inspect_scene(user_prompt: str = "") -> SceneState:
    """Deterministic scene inspection function.

    Reads the actual Blender scene via bpy and constructs a SceneState.
    """
    logger.info("Inspecting Blender scene...")

    objects: list[ObjectState] = []
    materials: list[MaterialState] = []
    lighting: list[LightState] = []
    camera: CameraState | None = None

    # Inspect objects using direct bpy.data access
    for obj in bpy.data.objects:
        # Determine status/visibility
        visible = obj.visible_get() if hasattr(obj, "visible_get") else True
        status = "active" if visible else "hidden"

        # Material assignment
        mat_name: str | None = None
        if obj.material_slots and len(obj.material_slots) > 0:
            slot = obj.material_slots[0]
            if slot.material:
                mat_name = slot.material.name

        # Modifiers
        modifiers: list[ModifierState] = []
        if hasattr(obj, "modifiers"):
            for mod in obj.modifiers:
                modifiers.append(
                    ModifierState(
                        name=mod.name,
                        modifier_type=mod.type,
                        show_viewport=getattr(mod, "show_viewport", True),
                    )
                )

        # Parent hierarchy
        parent_name = obj.parent.name if obj.parent else None

        # Build ObjectState
        obj_state = ObjectState(
            name=obj.name,
            type=obj.type,
            location=Vec3.from_tuple(list(obj.location)),
            rotation=Vec3.from_tuple(list(obj.rotation_euler)),
            scale=Vec3.from_tuple(list(obj.scale)),
            dimensions=Vec3.from_tuple(list(obj.dimensions)),
            material=mat_name,
            modifiers=modifiers,
            parent=parent_name,
            status=status,
        )
        objects.append(obj_state)

        # Gather lighting information
        if obj.type == "LIGHT":
            energy = 10.0
            if hasattr(obj, "data") and obj.data:
                energy = getattr(obj.data, "energy", 10.0)
            lighting.append(
                LightState(
                    name=obj.name,
                    type=getattr(obj.data, "type", "POINT") if hasattr(obj, "data") else "POINT",
                    location=Vec3.from_tuple(list(obj.location)),
                    energy=energy,
                )
            )

    # Inspect materials using direct bpy.data.materials access
    for mat in bpy.data.materials:
        base_color = (0.8, 0.8, 0.8, 1.0)
        metallic = 0.0
        roughness = 0.5

        if mat.use_nodes and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == "BSDF_PRINCIPLED":
                    # Get Base Color
                    if "Base Color" in node.inputs:
                        val = node.inputs["Base Color"].default_value
                        if isinstance(val, (list, tuple)) and len(val) >= 4:
                            base_color = (val[0], val[1], val[2], val[3])
                    # Get Metallic
                    if "Metallic" in node.inputs:
                        metallic = float(node.inputs["Metallic"].default_value)
                    # Get Roughness
                    if "Roughness" in node.inputs:
                        roughness = float(node.inputs["Roughness"].default_value)
                    break

        materials.append(
            MaterialState(
                name=mat.name,
                base_color=base_color,
                metallic=metallic,
                roughness=roughness,
            )
        )

    # Get active camera
    active_cam_obj = bpy.context.scene.camera if hasattr(bpy.context, "scene") and bpy.context.scene else None
    if active_cam_obj and active_cam_obj.type == "CAMERA":
        camera = CameraState(
            name=active_cam_obj.name,
            location=Vec3.from_tuple(list(active_cam_obj.location)),
            rotation=Vec3.from_tuple(list(active_cam_obj.rotation_euler)),
        )

    # Build SceneState
    scene_state = SceneState(
        user_prompt=user_prompt,
        objects=objects,
        materials=materials,
        camera=camera,
        lighting=lighting,
        status="generated" if len(objects) > 0 else "empty",
    )

    return scene_state
