"""
BlendPilot AI — Stage 5: Modeling Plan Schemas
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator

VALID_OPERATIONS = {
    "create_primitive",
    "set_transform",
    "duplicate_object",
    "delete_object",
    "edit_mesh",
    "create_material",
    "assign_material",
    "add_modifier",
    "apply_modifier",
    "setup_preview_camera",
    "setup_studio_lighting",
    "render_preview",
    "save_checkpoint",
    "save_project",
    "export_asset",
    "restore_checkpoint",
}


class ModelingStep(BaseModel):
    """A single step representing an atomic Blender core modeling operation."""
    step_id: int = Field(..., ge=1, description="Sequential, 1-indexed step number")
    operation: str = Field(..., description="Name of the Blender core operation to execute")
    target: str = Field(..., description="Name of the target object or material this step operates on")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Execution parameters for the operation")
    dependencies: list[int] = Field(default_factory=list, description="List of step_ids that must be completed first")

    # Legacy compatibility fields
    tool: str = Field(default="", description="Alias for operation")
    required_tool: str = Field(default="", description="Alias for operation")
    action: str = Field(default="", description="Step description")

    @model_validator(mode="before")
    @classmethod
    def populate_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            op = data.get("operation") or data.get("tool") or data.get("required_tool") or ""
            data["operation"] = op
            data["tool"] = op
            data["required_tool"] = op
            if "action" not in data:
                data["action"] = f"Execute {op} on {data.get('target', '')}"
        return data

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in VALID_OPERATIONS:
            raise ValueError(
                f"Unsupported operation: '{v}'. Must be one of: {', '.join(sorted(VALID_OPERATIONS))}"
            )
        return cleaned


class ModelingPlan(BaseModel):
    """Sequential plan containing ordered modeling operations."""
    steps: list[ModelingStep] = Field(..., description="List of ordered modeling steps")

    @field_validator("steps")
    @classmethod
    def validate_steps_order_and_dependencies(cls, v: list[ModelingStep]) -> list[ModelingStep]:
        # Validate sequential step_ids starting from 1
        step_ids = {step.step_id for step in v}
        for i in range(1, len(v) + 1):
            if i not in step_ids:
                raise ValueError(f"Plan step_ids must be sequential starting from 1, missing step_id: {i}")

        # Validate dependencies exist in previous steps (cannot depend on future or non-existent steps)
        for step in v:
            for dep in step.dependencies:
                if dep >= step.step_id:
                    raise ValueError(f"Step {step.step_id} cannot depend on future or self step: {dep}")
                if dep not in step_ids:
                    raise ValueError(f"Step {step.step_id} depends on non-existent step: {dep}")

        return v


class StepExecution(BaseModel):
    """Execution status and output for a single modeling step."""
    step_id: int = Field(..., description="ID of the executed step")
    operation: str = Field(..., description="Operation executed")
    target: str = Field(..., description="Target object or material")
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(default="", description="Status or error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Output details from core function")


class PlanExecution(BaseModel):
    """Complete summary of a plan's execution."""
    success: bool = Field(..., description="Whether all steps succeeded")
    created_objects: list[str] = Field(default_factory=list, description="All objects created during execution")
    materials_created: list[str] = Field(default_factory=list, description="All materials created during execution")
    step_executions: list[StepExecution] = Field(default_factory=list, description="Step-by-step executions")
    preview_image_path: str | None = Field(default=None, description="Path to generated preview render")


class RepairStep(BaseModel):
    """A single step in a targeted repair plan."""
    affected_object: str = Field(..., description="Name of the object to repair")
    problem: str = Field(..., description="Description of the issue being fixed")
    corrective_operation: str = Field(..., description="Name of the Blender core operation to execute")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Execution parameters for the operation")
    reason: str = Field(..., description="Explanation of why this operation fixes the problem")

    @field_validator("corrective_operation")
    @classmethod
    def validate_operation(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in VALID_OPERATIONS:
            raise ValueError(
                f"Unsupported operation: '{v}'. Must be one of: {', '.join(sorted(VALID_OPERATIONS))}"
            )
        return cleaned


class RepairPlan(BaseModel):
    """A targeted repair plan to fix scene issues without full regeneration."""
    steps: list[RepairStep] = Field(..., description="List of targeted repair steps")
