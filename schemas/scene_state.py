"""
BlendPilot AI — Stage 3: Scene State Models

Pydantic models representing the current, inspected state of a Blender scene.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal
from pydantic import BaseModel, Field


class Vec3(BaseModel):
    """An XYZ float triple."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def from_tuple(cls, t: tuple[float, float, float] | list[float]) -> "Vec3":
        return cls(x=float(t[0]), y=float(t[1]), z=float(t[2]))

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


class ModifierState(BaseModel):
    """Modifier summary on an object."""
    name: str
    modifier_type: str
    show_viewport: bool = True


class ObjectState(BaseModel):
    """State of an individual Blender object."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    type: str = "MESH"
    location: Vec3 = Field(default_factory=Vec3)
    rotation: Vec3 = Field(default_factory=Vec3)
    scale: Vec3 = Field(default_factory=lambda: Vec3(x=1.0, y=1.0, z=1.0))
    dimensions: Vec3 = Field(default_factory=Vec3)
    material: str | None = None
    modifiers: list[ModifierState] = Field(default_factory=list)
    parent: str | None = None
    status: str = "active"


class MaterialState(BaseModel):
    """State of an individual material."""
    name: str
    base_color: tuple[float, float, float, float] = (0.8, 0.8, 0.8, 1.0)
    metallic: float = 0.0
    roughness: float = 0.5


class CameraState(BaseModel):
    """State of the active camera."""
    name: str
    location: Vec3 = Field(default_factory=Vec3)
    rotation: Vec3 = Field(default_factory=Vec3)


class LightState(BaseModel):
    """State of an individual light."""
    name: str
    type: str = "POINT"
    location: Vec3 = Field(default_factory=Vec3)
    energy: float = 10.0


class ValidationReport(BaseModel):
    """Geometry validation report summary."""
    status: str = "PENDING"
    issues: list[dict[str, Any]] = Field(default_factory=list)


class VisionReport(BaseModel):
    """Visual critique report summary."""
    approved: bool = False
    criticism: str = ""


class SceneState(BaseModel):
    """State of the entire Blender scene."""
    user_prompt: str = ""
    objects: list[ObjectState] = Field(default_factory=list)
    materials: list[MaterialState] = Field(default_factory=list)
    camera: CameraState | None = None
    lighting: list[LightState] = Field(default_factory=list)
    validation_report: ValidationReport = Field(default_factory=ValidationReport)
    vision_report: VisionReport = Field(default_factory=VisionReport)
    repair_history: list[dict[str, Any]] = Field(default_factory=list)
    iteration: int = 0
    status: str = "empty"
