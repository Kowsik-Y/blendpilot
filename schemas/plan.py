"""
BlendPilot AI — Design Plan Schemas

Pydantic models for the step-by-step modeling plan
produced by Workflow 4 (Design Planning).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    """Completion status of a plan step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStep(BaseModel):
    """A single step in the modeling plan.

    Each step maps to one or more MCP tool calls.
    """

    step_id: int = Field(..., ge=1, description="Sequential step number")
    action: str = Field(..., min_length=1, description="What to do, e.g. 'Create main crate body'")
    target_object: str = Field(
        default="",
        description="Name of the Blender object this step operates on",
    )
    expected_result: str = Field(
        default="",
        description="What the scene should look like after this step",
    )
    required_tool: str = Field(
        default="",
        description="The MCP tool needed, e.g. 'create_primitive', 'add_modifier'",
    )
    dependencies: list[int] = Field(
        default_factory=list,
        description="step_id values that must be completed first",
    )
    status: StepStatus = Field(
        default=StepStatus.PENDING,
        description="Current completion status",
    )
    error_message: str | None = None


class DesignPlan(BaseModel):
    """Complete modeling plan for an asset.

    Generated before any Blender modifications begin.
    Stored in LangGraph state and updated as steps execute.
    """

    plan_id: str = Field(..., description="Unique identifier for this plan")
    asset_type: str = Field(..., description="What is being built")
    steps: list[PlanStep] = Field(default_factory=list)
    total_steps: int = Field(default=0, ge=0)
    completed_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)

    @property
    def is_complete(self) -> bool:
        """Check if all steps are completed or skipped."""
        return all(
            s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
            for s in self.steps
        )

    @property
    def current_step(self) -> PlanStep | None:
        """Get the next pending or in-progress step."""
        for step in self.steps:
            if step.status in (StepStatus.PENDING, StepStatus.IN_PROGRESS):
                return step
        return None
