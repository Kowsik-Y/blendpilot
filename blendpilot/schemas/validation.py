"""
BlendPilot AI — Validation Result Schemas

Pydantic models for geometry QA and visual critique results,
used by Workflows 7 and 8.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Issue severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(str, Enum):
    """Types of geometry validation issues."""

    TRIANGLE_OVER_BUDGET = "TRIANGLE_OVER_BUDGET"
    NON_MANIFOLD = "NON_MANIFOLD"
    FLIPPED_NORMALS = "FLIPPED_NORMALS"
    DUPLICATE_VERTICES = "DUPLICATE_VERTICES"
    MISSING_MATERIAL = "MISSING_MATERIAL"
    UNAPPLIED_TRANSFORM = "UNAPPLIED_TRANSFORM"
    BAD_NAMING = "BAD_NAMING"
    WRONG_ORIGIN = "WRONG_ORIGIN"
    DIMENSION_MISMATCH = "DIMENSION_MISMATCH"
    NGON_DETECTED = "NGON_DETECTED"
    MISSING_UV = "MISSING_UV"
    INTERSECTING_GEOMETRY = "INTERSECTING_GEOMETRY"


class ValidationIssue(BaseModel):
    """A single validation issue found during geometry QA."""

    issue_type: IssueType
    object_name: str = Field(..., description="Name of the affected Blender object")
    severity: Severity = Field(default=Severity.MEDIUM)
    message: str = Field(default="", description="Human-readable description of the issue")
    auto_fixable: bool = Field(
        default=False,
        description="Whether this issue can be automatically repaired",
    )


class ValidationResult(BaseModel):
    """Result of a complete geometry QA pass.

    Matches the structure from plan Section 5, Workflow 7.
    """

    status: str = Field(
        ...,
        description="Overall result: PASS or FAIL",
        pattern=r"^(PASS|FAIL)$",
    )
    object_name: str = Field(default="", description="Primary object validated")
    triangle_count: int = Field(default=0, ge=0)
    triangle_limit: int = Field(default=0, ge=0)
    vertex_count: int = Field(default=0, ge=0)
    face_count: int = Field(default=0, ge=0)
    dimensions: tuple[float, float, float] = (0.0, 0.0, 0.0)
    issues: list[ValidationIssue] = Field(default_factory=list)
    issues_by_severity: dict[str, int] = Field(default_factory=dict)

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any critical-severity issues."""
        return any(i.severity == Severity.CRITICAL for i in self.issues)

    @property
    def auto_fixable_count(self) -> int:
        """Count of issues that can be automatically repaired."""
        return sum(1 for i in self.issues if i.auto_fixable)


class VisualCritiqueIssue(BaseModel):
    """A single issue identified by the visual critic."""

    target: str = Field(..., description="Object or area with the issue")
    problem: str = Field(..., description="Description of the visual problem")
    severity: Severity = Field(default=Severity.MEDIUM)
    recommended_change: str = Field(
        default="",
        description="Suggested fix from the vision model",
    )


class VisualCritiqueResult(BaseModel):
    """Result of a visual critique pass (Workflow 8).

    The vision model scores the render and provides structured feedback.
    """

    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall quality score from 0.0 (terrible) to 1.0 (perfect)",
    )
    issues: list[VisualCritiqueIssue] = Field(default_factory=list)
    iteration: int = Field(default=1, ge=1, description="Which critique iteration this is")
    max_iterations: int = Field(default=3, ge=1)
    recommendation: str = Field(
        default="",
        description="Overall recommendation: APPROVE, REVISE, or REJECT",
    )
