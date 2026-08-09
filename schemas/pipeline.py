"""
BlendPilot AI — Stage 7: Pipeline Result Schema

Typed output model for the synchronous pipeline run.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from schemas.intent import IntentSpec
from schemas.plan_state import ModelingPlan
from schemas.scene_state import SceneState


class PipelineResult(BaseModel):
    """Complete, typed result of one synchronous pipeline run."""

    intent: IntentSpec = Field(..., description="Parsed design intent")
    plan: ModelingPlan = Field(..., description="Generated modeling plan")
    generation: dict[str, Any] = Field(..., description="Generation agent execution output (PlanExecution dict)")
    scene_state: SceneState | None = Field(default=None, description="Blender scene snapshot, or None if bpy unavailable")
    blend_path: str | None = Field(default=None, description="Absolute path to saved .blend file, or None")
    preview_path: str | None = Field(default=None, description="Absolute path to rendered preview image, or None")
    success: bool = Field(..., description="True if all pipeline steps succeeded")
    elapsed_seconds: float = Field(default=0.0, description="Wall-clock time for the full pipeline run")
    report_lines: list[str] = Field(default_factory=list, description="Human-readable lines of the execution report")
