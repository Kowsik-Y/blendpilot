"""
BlendPilot AI — Scene Data Schemas

Pydantic models for representing the Blender scene state,
produced by Workflow 2 (Scene Understanding).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ObjectType(str, Enum):
    """Blender object types we track."""

    MESH = "MESH"
    CAMERA = "CAMERA"
    LIGHT = "LIGHT"
    EMPTY = "EMPTY"
    CURVE = "CURVE"
    OTHER = "OTHER"


class TransformInfo(BaseModel):
    """Object transform data."""

    location: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)


class ModifierInfo(BaseModel):
    """Summary of a single modifier on an object."""

    name: str
    modifier_type: str
    show_viewport: bool = True


class MaterialSlot(BaseModel):
    """Summary of a material slot on an object."""

    slot_index: int
    material_name: str | None = None


class ObjectInfo(BaseModel):
    """Detailed information about a single Blender object."""

    name: str
    object_type: ObjectType
    transform: TransformInfo = Field(default_factory=TransformInfo)
    dimensions: tuple[float, float, float] = (0.0, 0.0, 0.0)
    parent: str | None = None
    collection: str = "Scene Collection"
    modifiers: list[ModifierInfo] = Field(default_factory=list)
    material_slots: list[MaterialSlot] = Field(default_factory=list)
    visible: bool = True
    mesh_stats: MeshStatistics | None = None


class MeshStatistics(BaseModel):
    """Mesh-level statistics for a single object."""

    object_name: str
    vertex_count: int = Field(default=0, ge=0)
    edge_count: int = Field(default=0, ge=0)
    face_count: int = Field(default=0, ge=0)
    triangle_count: int = Field(default=0, ge=0)
    has_ngons: bool = False
    dimensions: tuple[float, float, float] = (0.0, 0.0, 0.0)
    bounding_box_volume: float = Field(default=0.0, ge=0)
    non_manifold_edges: int | None = None
    flipped_faces: int | None = None


class SceneSummary(BaseModel):
    """Structured summary of the current Blender scene.

    Produced by the Scene Understanding workflow and used
    by downstream agents to understand the current project state.
    """

    blend_file: str = Field(default="", description="Path to current .blend file")
    object_count: int = Field(default=0, ge=0)
    objects: list[ObjectInfo] = Field(default_factory=list)
    collections: list[str] = Field(default_factory=list)
    has_camera: bool = False
    has_lights: bool = False
    active_object: str | None = None
    frame_current: int = 1
    render_engine: str = "BLENDER_EEVEE"
