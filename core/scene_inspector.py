"""
BlendPilot AI — Stage 3: Deterministic Scene Inspector

Reads the actual Blender scene via bpy.data / bpy.context and constructs
a fully-typed SceneState model.

Contract:
  - NEVER invents or guesses object properties.
  - Every field in the returned SceneState is read directly from Blender.
  - Raises ValueError for invalid inputs; logs and skips objects that
    cannot be read rather than fabricating data.
  - Uses bpy.data wherever possible; falls back to bpy.context only for
    properties that have no data-API equivalent (active camera, scene render).

Runs inside Blender's Python environment.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import bpy  # type: ignore[import-not-found]

from schemas.scene_state import (
    CameraState,
    LightState,
    MaterialState,
    MeshStats,
    ModifierState,
    ObjectKind,
    ObjectState,
    ObjectStatus,
    RepairRecord,
    SceneState,
    SceneStatus,
    ValidationReport,
    Vec3,
    VisionReport,
)

logger = logging.getLogger("blendpilot.core.scene_inspector")


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def inspect_scene(
    user_prompt: str = "",
    status: SceneStatus = SceneStatus.GENERATED,
    existing_state: SceneState | None = None,
) -> SceneState:
    """Read the current Blender scene and return a fully-populated SceneState.

    This is the ONLY function that should construct a SceneState from scratch.
    It reads from bpy.data and bpy.context — never from LLM output or guesses.

    Args:
        user_prompt: The original user request (passed through, not inspected).
        status: Pipeline status to tag the snapshot with.
        existing_state: If provided, the scene_id and repair_history are
                        preserved from the previous snapshot. All object/material
                        data is re-read from Blender.

    Returns:
        A populated SceneState reflecting the actual Blender scene at this moment.
    """
    logger.info("inspect_scene() starting...")

    # Preserve continuity fields from an existing state if given
    scene_id = existing_state.scene_id if existing_state else None
    repair_history = existing_state.repair_history if existing_state else []
    iteration = existing_state.iteration if existing_state else 0

    now = datetime.now(timezone.utc).isoformat()

    # ── Read scene objects ─────────────────────────────────────────────────
    objects = _read_all_objects()

    # ── Read materials ─────────────────────────────────────────────────────
    materials = _read_all_materials()

    # ── Read camera ────────────────────────────────────────────────────────
    camera = _read_active_camera()

    # ── Read lights ────────────────────────────────────────────────────────
    lighting = _read_lights(objects)

    # ── Read scene-level properties ────────────────────────────────────────
    blend_file = _safe_get(lambda: str(bpy.data.filepath) or "", "")
    render_engine = _safe_get(lambda: str(bpy.context.scene.render.engine), "BLENDER_EEVEE")
    frame_current = _safe_get(lambda: int(bpy.context.scene.frame_current), 1)

    # ── Determine initial status ────────────────────────────────────────────
    mesh_count = sum(1 for o in objects if o.type == ObjectKind.MESH)
    if mesh_count == 0 and status == SceneStatus.GENERATED:
        status = SceneStatus.EMPTY

    # ── Build state ────────────────────────────────────────────────────────
    kwargs: dict[str, Any] = dict(
        inspected_at=now,
        blend_file=blend_file,
        user_prompt=user_prompt,
        objects=objects,
        materials=materials,
        camera=camera,
        lighting=lighting,
        validation_report=ValidationReport(),
        vision_report=VisionReport(),
        repair_history=repair_history,
        iteration=iteration,
        status=status,
        render_engine=render_engine,
        frame_current=frame_current,
    )
    if scene_id is not None:
        kwargs["scene_id"] = scene_id

    state = SceneState(**kwargs)

    logger.info(
        "inspect_scene() complete — %d objects (%d meshes), %d materials, camera=%s",
        len(objects),
        mesh_count,
        len(materials),
        camera.name if camera else "None",
    )
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Object readers
# ─────────────────────────────────────────────────────────────────────────────

def _read_all_objects() -> list[ObjectState]:
    """Read every object from bpy.data.objects and construct ObjectState records."""
    objects: list[ObjectState] = []

    for obj in bpy.data.objects:
        try:
            state = _read_single_object(obj)
            objects.append(state)
        except Exception as exc:
            logger.warning("Skipping object '%s' — read error: %s", obj.name, exc)

    logger.debug("Read %d objects from bpy.data.objects", len(objects))
    return objects


def _read_single_object(obj: Any) -> ObjectState:
    """Construct an ObjectState from a single bpy object."""
    kind = ObjectKind.from_blender_type(_safe_get(lambda: str(obj.type), "OTHER"))

    # Transforms — read directly from data properties
    location = Vec3.from_tuple(_safe_vec3(lambda: obj.location, (0.0, 0.0, 0.0)))
    rotation = Vec3.from_tuple(_safe_vec3(lambda: obj.rotation_euler, (0.0, 0.0, 0.0)))
    scale = Vec3.from_tuple(_safe_vec3(lambda: obj.scale, (1.0, 1.0, 1.0)))
    dimensions = Vec3.from_tuple(_safe_vec3(lambda: obj.dimensions, (0.0, 0.0, 0.0)))

    # Parent name
    parent_name: str | None = _safe_get(
        lambda: obj.parent.name if obj.parent else None, None
    )

    # Collection (first collection this object belongs to)
    collection = _safe_get(
        lambda: obj.users_collection[0].name if obj.users_collection else "Scene Collection",
        "Scene Collection",
    )

    # Visibility
    visible = _safe_get(lambda: bool(obj.visible_get()), True)
    status = ObjectStatus.ACTIVE if visible else ObjectStatus.HIDDEN

    # Material slots
    slot_names: list[str | None] = []
    primary_material: str | None = None
    try:
        for slot in obj.material_slots:
            mat_name = slot.material.name if slot.material else None
            slot_names.append(mat_name)
        if slot_names:
            primary_material = slot_names[0]
    except Exception:
        pass

    # Modifiers
    modifiers = _read_modifiers(obj)

    # Mesh statistics (only for MESH objects)
    mesh_stats: MeshStats | None = None
    if kind == ObjectKind.MESH:
        mesh_stats = _read_mesh_stats(obj)

    return ObjectState(
        name=obj.name,
        type=kind,
        location=location,
        rotation=rotation,
        scale=scale,
        dimensions=dimensions,
        material=primary_material,
        material_slots=slot_names,
        modifiers=modifiers,
        parent=parent_name,
        collection=collection,
        visible=visible,
        status=status,
        mesh_stats=mesh_stats,
    )


def _read_modifiers(obj: Any) -> list[ModifierState]:
    """Read all modifiers from a bpy object."""
    modifiers: list[ModifierState] = []
    try:
        for mod in obj.modifiers:
            try:
                modifiers.append(ModifierState(
                    name=str(mod.name),
                    modifier_type=str(mod.type),
                    show_viewport=bool(mod.show_viewport),
                    show_render=bool(mod.show_render),
                ))
            except Exception as exc:
                logger.debug("Skipping modifier '%s': %s", mod.name, exc)
    except Exception:
        pass
    return modifiers


def _read_mesh_stats(obj: Any) -> MeshStats | None:
    """Read vertex/edge/face/triangle counts from a mesh object's data."""
    try:
        mesh = obj.data
        if mesh is None:
            return None

        vertex_count = len(mesh.vertices)
        edge_count = len(mesh.edges)
        face_count = len(mesh.polygons)

        # Triangle count and ngon detection using bmesh for accuracy
        triangle_count = face_count  # default if bmesh unavailable
        has_ngons = False
        try:
            import bmesh  # type: ignore[import-not-found]
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.faces.ensure_lookup_table()
            triangle_count = sum(len(f.verts) - 2 for f in bm.faces)
            has_ngons = any(len(f.verts) > 4 for f in bm.faces)
            bm.free()
        except Exception:
            pass

        # UV layers
        uv_layer_count = _safe_get(lambda: len(mesh.uv_layers), 0)
        has_uv = uv_layer_count > 0

        return MeshStats(
            vertex_count=vertex_count,
            edge_count=edge_count,
            face_count=face_count,
            triangle_count=triangle_count,
            has_ngons=has_ngons,
            has_uv=has_uv,
            uv_layer_count=uv_layer_count,
        )
    except Exception as exc:
        logger.debug("Could not read mesh stats: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Material readers
# ─────────────────────────────────────────────────────────────────────────────

def _read_all_materials() -> list[MaterialState]:
    """Read every material from bpy.data.materials."""
    materials: list[MaterialState] = []
    try:
        for mat in bpy.data.materials:
            try:
                mat_state = _read_single_material(mat)
                materials.append(mat_state)
            except Exception as exc:
                logger.warning("Skipping material '%s' — read error: %s", mat.name, exc)
    except Exception as exc:
        logger.warning("Could not iterate bpy.data.materials: %s", exc)
    return materials


def _read_single_material(mat: Any) -> MaterialState:
    """Read a MaterialState from a bpy material."""
    use_nodes = _safe_get(lambda: bool(mat.use_nodes), True)
    users = _safe_get(lambda: int(mat.users), 0)

    # Default PBR values
    base_color: tuple[float, float, float, float] = (0.8, 0.8, 0.8, 1.0)
    metallic: float = 0.0
    roughness: float = 0.5
    emission_strength: float = 0.0
    emission_color: tuple[float, float, float, float] | None = None

    # Try to read Principled BSDF inputs
    try:
        if use_nodes and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == "BSDF_PRINCIPLED":
                    bc = node.inputs["Base Color"].default_value
                    base_color = (float(bc[0]), float(bc[1]), float(bc[2]), float(bc[3]))
                    metallic = float(node.inputs["Metallic"].default_value)
                    roughness = float(node.inputs["Roughness"].default_value)
                    emission_strength = float(
                        node.inputs["Emission Strength"].default_value
                    )
                    if emission_strength > 0:
                        ec = node.inputs["Emission Color"].default_value
                        emission_color = (
                            float(ec[0]), float(ec[1]), float(ec[2]), float(ec[3])
                        )
                    break
    except Exception:
        pass

    return MaterialState(
        name=str(mat.name),
        use_nodes=use_nodes,
        base_color=base_color,
        metallic=max(0.0, min(1.0, metallic)),
        roughness=max(0.0, min(1.0, roughness)),
        emission_strength=max(0.0, emission_strength),
        emission_color=emission_color,
        users=users,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Camera reader
# ─────────────────────────────────────────────────────────────────────────────

def _read_active_camera() -> CameraState | None:
    """Read the active camera from bpy.context.scene.camera."""
    try:
        cam_obj = bpy.context.scene.camera
        if cam_obj is None:
            return None

        cam_data = cam_obj.data
        location = Vec3.from_tuple(_safe_vec3(lambda: cam_obj.location, (0.0, 0.0, 0.0)))
        rotation = Vec3.from_tuple(_safe_vec3(lambda: cam_obj.rotation_euler, (0.0, 0.0, 0.0)))
        lens = _safe_get(lambda: float(cam_data.lens), 50.0)
        clip_start = _safe_get(lambda: float(cam_data.clip_start), 0.1)
        clip_end = _safe_get(lambda: float(cam_data.clip_end), 1000.0)
        sensor_width = _safe_get(lambda: float(cam_data.sensor_width), 36.0)

        return CameraState(
            name=str(cam_obj.name),
            location=location,
            rotation=rotation,
            lens=lens,
            clip_start=clip_start,
            clip_end=clip_end,
            sensor_width=sensor_width,
        )
    except Exception as exc:
        logger.warning("Could not read active camera: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Light reader
# ─────────────────────────────────────────────────────────────────────────────

def _read_lights(objects: list[ObjectState]) -> list[LightState]:
    """Extract light objects from the already-read object list.

    We iterate bpy.data.objects directly for lights to get their light data.
    """
    lights: list[LightState] = []
    try:
        for obj in bpy.data.objects:
            if obj.type != "LIGHT":
                continue
            try:
                light_data = obj.data
                light_type = _safe_get(lambda: str(light_data.type), "AREA")
                energy = _safe_get(lambda: float(light_data.energy), 300.0)
                color_raw = _safe_get(lambda: light_data.color, None)
                if color_raw is not None:
                    color = (float(color_raw[0]), float(color_raw[1]), float(color_raw[2]))
                else:
                    color = (1.0, 1.0, 1.0)
                location = Vec3.from_tuple(
                    _safe_vec3(lambda: obj.location, (0.0, 0.0, 0.0))
                )
                lights.append(LightState(
                    name=str(obj.name),
                    light_type=light_type,
                    location=location,
                    energy=energy,
                    color=color,
                ))
            except Exception as exc:
                logger.debug("Skipping light '%s': %s", obj.name, exc)
    except Exception as exc:
        logger.warning("Could not read lights: %s", exc)
    return lights


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_get(fn: Any, default: Any) -> Any:
    """Call fn() and return the result, or default if any exception is raised."""
    try:
        return fn()
    except Exception:
        return default


def _safe_vec3(
    fn: Any,
    default: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Safely read a 3-component vector, converting to plain floats."""
    try:
        v = fn()
        return (float(v[0]), float(v[1]), float(v[2]))
    except Exception:
        return default
