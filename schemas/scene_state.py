"""
BlendPilot AI — Stage 3: Scene State Models

Pydantic models representing the complete, inspected state of a Blender scene.

These models are:
  - Fully serializable to / from JSON (model_dump(mode="json"))
  - Constructed ONLY from actual Blender data — never invented
  - Used by the Geometry QA, Visual Critic, Decision, and Repair agents

Model hierarchy:
  ObjectState        — single object in the scene
  MaterialState      — single material in bpy.data.materials
  CameraState        — active camera properties
  LightState         — individual light in the scene
  RepairRecord       — a single repair operation entry
  ValidationReport   — aggregate geometry QA result embedded in SceneState
  VisionReport       — aggregate visual critique result embedded in SceneState
  SceneState         — root model: the complete inspected scene
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class ObjectStatus(str, Enum):
    """Lifecycle status of a tracked object."""
    ACTIVE = "active"         # Present and visible in scene
    HIDDEN = "hidden"         # Present but not visible in viewport
    EXCLUDED = "excluded"     # Excluded from view layer
    DELETED = "deleted"       # Was tracked, now removed (tombstone)


class ObjectKind(str, Enum):
    """Blender object types we track."""
    MESH = "MESH"
    CAMERA = "CAMERA"
    LIGHT = "LIGHT"
    EMPTY = "EMPTY"
    CURVE = "CURVE"
    ARMATURE = "ARMATURE"
    LATTICE = "LATTICE"
    FONT = "FONT"
    OTHER = "OTHER"

    @classmethod
    def from_blender_type(cls, btype: str) -> "ObjectKind":
        """Convert a raw Blender type string to ObjectKind."""
        try:
            return cls(btype)
        except ValueError:
            return cls.OTHER


class SceneStatus(str, Enum):
    """Pipeline status of the scene."""
    EMPTY = "empty"               # No user-created objects yet
    GENERATING = "generating"     # Generation agent is running
    GENERATED = "generated"       # Generation complete, not yet validated
    VALIDATING = "validating"     # QA agents running
    NEEDS_REPAIR = "needs_repair" # Validation failed, repair needed
    REPAIRING = "repairing"       # Repair agent running
    APPROVED = "approved"         # Passed all checks, ready for export
    EXPORTED = "exported"         # Export complete
    FAILED = "failed"             # Pipeline failed unrecoverably


# ─────────────────────────────────────────────────────────────────────────────
# Sub-models
# ─────────────────────────────────────────────────────────────────────────────

class Vec3(BaseModel):
    """An immutable XYZ float triple. Serializes as [x, y, z]."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def from_tuple(cls, t: tuple[float, float, float] | list[float]) -> "Vec3":
        """Construct from any 3-element sequence."""
        return cls(x=float(t[0]), y=float(t[1]), z=float(t[2]))

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def model_dump(self, **kw: Any) -> dict[str, Any]:  # type: ignore[override]
        return {"x": self.x, "y": self.y, "z": self.z}


class ModifierState(BaseModel):
    """State snapshot of a single modifier on an object."""
    name: str
    modifier_type: str
    show_viewport: bool = True
    show_render: bool = True
    properties: dict[str, Any] = Field(default_factory=dict)


class MaterialState(BaseModel):
    """State snapshot of a material in bpy.data.materials."""
    name: str
    use_nodes: bool = True
    base_color: tuple[float, float, float, float] = (0.8, 0.8, 0.8, 1.0)
    metallic: float = Field(default=0.0, ge=0.0, le=1.0)
    roughness: float = Field(default=0.5, ge=0.0, le=1.0)
    emission_strength: float = Field(default=0.0, ge=0.0)
    emission_color: tuple[float, float, float, float] | None = None
    users: int = Field(default=0, ge=0, description="Number of objects using this material")


class CameraState(BaseModel):
    """State of the active camera in the scene."""
    name: str
    location: Vec3 = Field(default_factory=Vec3)
    rotation: Vec3 = Field(default_factory=Vec3)
    lens: float = Field(default=50.0, gt=0, description="Focal length in mm")
    clip_start: float = Field(default=0.1, gt=0)
    clip_end: float = Field(default=1000.0, gt=0)
    sensor_width: float = Field(default=36.0, gt=0)


class LightState(BaseModel):
    """State of a single light in the scene."""
    name: str
    light_type: str = "AREA"  # POINT, SUN, SPOT, AREA
    location: Vec3 = Field(default_factory=Vec3)
    energy: float = Field(default=300.0, ge=0.0)
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)


class MeshStats(BaseModel):
    """Deterministic mesh statistics for a single object."""
    vertex_count: int = Field(default=0, ge=0)
    edge_count: int = Field(default=0, ge=0)
    face_count: int = Field(default=0, ge=0)
    triangle_count: int = Field(default=0, ge=0)
    has_ngons: bool = False
    has_uv: bool = False
    uv_layer_count: int = Field(default=0, ge=0)


class ValidationReport(BaseModel):
    """Embedded geometry QA report within SceneState."""
    status: Literal["PASS", "FAIL", "PENDING"] = "PENDING"
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    checked_at: str = ""
    issues: list[dict[str, Any]] = Field(default_factory=list)
    issues_by_severity: dict[str, int] = Field(default_factory=dict)
    auto_fixable_count: int = Field(default=0, ge=0)


class VisionReport(BaseModel):
    """Embedded visual critique report within SceneState."""
    approved: bool = False
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    aesthetic_score: float = Field(default=0.0, ge=0.0, le=1.0)
    spec_compliance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    critique_at: str = ""
    strengths: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


class RepairRecord(BaseModel):
    """A single entry in the repair history log."""
    iteration: int = Field(default=1, ge=1)
    priority_issue: Literal["geometry", "visual", "none"] = "none"
    timestamp: str = ""
    operations: list[str] = Field(default_factory=list, description="Tool calls executed")
    outcome: Literal["success", "partial", "failed"] = "success"
    notes: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# ObjectState
# ─────────────────────────────────────────────────────────────────────────────

class ObjectState(BaseModel):
    """Complete state snapshot of a single Blender object.

    All fields are read directly from Blender's data API — never invented.
    """

    # Identity
    id: str = Field(
        default_factory=lambda: uuid.uuid4().hex[:12],
        description="Stable internal ID, generated once on first inspection",
    )
    name: str = Field(..., description="Blender object name (must match bpy.data.objects)")
    type: ObjectKind = Field(
        default=ObjectKind.MESH,
        description="Blender object type",
    )

    # Transforms (read from obj.location, obj.rotation_euler, obj.scale)
    location: Vec3 = Field(default_factory=Vec3)
    rotation: Vec3 = Field(default_factory=Vec3, description="Euler rotation in radians")
    scale: Vec3 = Field(default_factory=lambda: Vec3(x=1.0, y=1.0, z=1.0))
    dimensions: Vec3 = Field(default_factory=Vec3, description="World-space bounding box size")

    # Material (primary slot name, or None)
    material: str | None = Field(
        default=None,
        description="Name of the first material slot, or None if unassigned",
    )
    # All material slots
    material_slots: list[str | None] = Field(
        default_factory=list,
        description="Ordered list of material names per slot (None = empty slot)",
    )

    # Modifiers
    modifiers: list[ModifierState] = Field(default_factory=list)

    # Hierarchy
    parent: str | None = Field(
        default=None,
        description="Name of the parent object, or None if root",
    )
    collection: str = Field(
        default="Scene Collection",
        description="Primary collection this object belongs to",
    )

    # Visibility & status
    visible: bool = Field(default=True, description="Viewport visibility")
    status: ObjectStatus = Field(default=ObjectStatus.ACTIVE)

    # Mesh stats (None for non-MESH objects)
    mesh_stats: MeshStats | None = Field(
        default=None,
        description="Populated only for MESH-type objects",
    )

    @field_validator("name")
    @classmethod
    def name_must_be_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("ObjectState.name cannot be empty")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# SceneState
# ─────────────────────────────────────────────────────────────────────────────

class SceneState(BaseModel):
    """Complete, inspected state of a Blender scene.

    This is the single source of truth used by all downstream pipeline stages:
    Geometry QA → Visual Critic → Decision Agent → Repair Agent → Export

    Contract:
      - All objects listed in `objects` must exist in the Blender scene.
      - This model must never be manually constructed with invented data.
      - Use `core.scene_inspector.inspect_scene()` to build this model.
      - Serializes fully to JSON via model_dump(mode="json").
    """

    # ── Session ──────────────────────────────────────────────────────────────
    scene_id: str = Field(
        default_factory=lambda: uuid.uuid4().hex[:16],
        description="Unique identifier for this scene inspection snapshot",
    )
    inspected_at: str = Field(
        default="",
        description="ISO-8601 UTC timestamp of when inspect_scene() ran",
    )
    blend_file: str = Field(
        default="",
        description="Absolute path to the .blend file, or empty if unsaved",
    )

    # ── User Context ─────────────────────────────────────────────────────────
    user_prompt: str = Field(
        default="",
        description="The original user natural-language request for this asset",
    )

    # ── Scene Objects ─────────────────────────────────────────────────────────
    objects: list[ObjectState] = Field(
        default_factory=list,
        description="All objects in the scene, exactly as read from Blender",
    )

    # ── Materials ─────────────────────────────────────────────────────────────
    materials: list[MaterialState] = Field(
        default_factory=list,
        description="All materials in bpy.data.materials",
    )

    # ── Camera ────────────────────────────────────────────────────────────────
    camera: CameraState | None = Field(
        default=None,
        description="Active camera state, or None if no camera in scene",
    )

    # ── Lighting ──────────────────────────────────────────────────────────────
    lighting: list[LightState] = Field(
        default_factory=list,
        description="All LIGHT objects currently in the scene",
    )

    # ── Validation & Vision ───────────────────────────────────────────────────
    validation_report: ValidationReport = Field(
        default_factory=ValidationReport,
        description="Latest geometry QA result — PENDING until QA agent runs",
    )
    vision_report: VisionReport = Field(
        default_factory=VisionReport,
        description="Latest visual critique result — unpopulated until critic runs",
    )

    # ── Repair History ────────────────────────────────────────────────────────
    repair_history: list[RepairRecord] = Field(
        default_factory=list,
        description="Chronological log of repair operations performed",
    )

    # ── Pipeline Counters ─────────────────────────────────────────────────────
    iteration: int = Field(
        default=0,
        ge=0,
        description="How many repair+validation loops have completed",
    )

    # ── Status ────────────────────────────────────────────────────────────────
    status: SceneStatus = Field(
        default=SceneStatus.EMPTY,
        description="Current pipeline status of the scene",
    )
    render_engine: str = Field(default="BLENDER_EEVEE")
    frame_current: int = Field(default=1)

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def mesh_objects(self) -> list[ObjectState]:
        """Return only MESH-type objects."""
        return [o for o in self.objects if o.type == ObjectKind.MESH]

    @property
    def object_names(self) -> list[str]:
        """Return the names of all tracked objects."""
        return [o.name for o in self.objects]

    @property
    def has_camera(self) -> bool:
        return self.camera is not None

    @property
    def has_lighting(self) -> bool:
        return len(self.lighting) > 0

    @property
    def total_triangle_count(self) -> int:
        """Sum of triangle counts across all mesh objects."""
        return sum(
            (o.mesh_stats.triangle_count if o.mesh_stats else 0)
            for o in self.mesh_objects
        )

    def get_object(self, name: str) -> ObjectState | None:
        """Look up a tracked object by name."""
        for obj in self.objects:
            if obj.name == name:
                return obj
        return None

    def get_material(self, name: str) -> MaterialState | None:
        """Look up a tracked material by name."""
        for mat in self.materials:
            if mat.name == name:
                return mat
        return None

    def add_repair_record(self, record: RepairRecord) -> None:
        """Append a repair record and increment the iteration counter."""
        self.repair_history.append(record)
        self.iteration = max(self.iteration, record.iteration)

    @model_validator(mode="after")
    def set_inspected_at_if_empty(self) -> "SceneState":
        if not self.inspected_at:
            self.inspected_at = datetime.now(timezone.utc).isoformat()
        return self
