"""
BlendPilot AI — Design Plan Schemas

Pydantic models for the step-by-step modeling plan
produced by Workflow 4 (Design Planning).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

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
    action: str = Field(default="", description="What to do, e.g. 'Create main crate body'")
    description: str | None = Field(default=None, description="Description alias for action")
    target_object: str | list[str] | None = Field(
        default="",
        description="Name of the Blender object this step operates on",
    )
    expected_result: str | None = Field(
        default="",
        description="What the scene should look like after this step",
    )
    expected_outcome: str | None = Field(default=None, description="Alias for expected_result")
    required_tool: str | None = Field(
        default="",
        description="The MCP tool needed, e.g. 'create_primitive', 'add_modifier'",
    )
    tool: str | None = Field(default=None, description="Alias for required_tool")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Tool invocation parameters")
    dependencies: list[int] = Field(
        default_factory=list,
        description="step_id values that must be completed first",
    )
    status: StepStatus = Field(
        default=StepStatus.PENDING,
        description="Current completion status",
    )
    error_message: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if isinstance(self.target_object, list):
            self.target_object = ", ".join(self.target_object)
        elif self.target_object is None:
            self.target_object = ""

        if not self.action and self.description:
            self.action = self.description
        if not self.description and self.action:
            self.description = self.action
        if not self.required_tool and self.tool:
            self.required_tool = self.tool
        if not self.tool and self.required_tool:
            self.tool = self.required_tool
        if not self.expected_result and self.expected_outcome:
            self.expected_result = self.expected_outcome
        if not self.expected_outcome and self.expected_result:
            self.expected_outcome = self.expected_result


class DesignPlan(BaseModel):
    """Complete modeling plan for an asset.

    Generated before any Blender modifications begin.
    Stored in LangGraph state and updated as steps execute.
    """

    plan_id: str = Field(default="", description="Plan identifier")
    spec_id: str = Field(default="", description="ID of the DesignSpec this plan implements")
    asset_type: str = Field(default="", description="Type of asset being created")
    steps: list[PlanStep] = Field(
        ...,
        min_length=1,
        description="Ordered list of steps to execute",
    )
    total_steps: int = Field(default=0, description="Total number of steps in plan")
    current_step_index: int = Field(
        default=0,
        ge=0,
        description="Index of the currently executing step",
    )
    completed_count: int = Field(default=0, description="Completed steps count")
    status: StepStatus = Field(
        default=StepStatus.PENDING,
        description="Overall plan completion status",
    )

    def model_post_init(self, __context: Any) -> None:
        if not self.plan_id and self.spec_id:
            self.plan_id = self.spec_id
        if not self.spec_id and self.plan_id:
            self.spec_id = self.plan_id
        if self.total_steps == 0 and self.steps:
            self.total_steps = len(self.steps)

    @property
    def is_complete(self) -> bool:
        """Check if all steps have completed successfully."""
        return all(s.status == StepStatus.COMPLETED for s in self.steps)

    @property
    def current_step(self) -> PlanStep | None:
        """Return the next pending or in-progress step, or None if complete."""
        for s in self.steps:
            if s.status in [StepStatus.PENDING, StepStatus.IN_PROGRESS]:
                return s
        return None
