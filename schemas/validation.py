"""
BlendPilot AI — Validation Result Schemas

Pydantic models for geometry QA and visual critique results,
used by Workflows 7 and 8.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Issue severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Alias for backward compatibility
IssueSeverity = Severity


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
    TOPOLOGY_ERROR = "TOPOLOGY_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class ValidationIssue(BaseModel):
    """A single validation issue found during geometry QA."""

    issue_type: IssueType | str = Field(default=IssueType.TOPOLOGY_ERROR)
    type: str | None = Field(default=None, description="Issue type name alias")
    object_name: str = Field(default="", description="Name of the affected Blender object")
    severity: Severity = Field(default=Severity.MEDIUM)
    message: str = Field(default="", description="Human-readable description of the issue")
    description: str | None = Field(default=None, description="Detailed description alias")
    auto_fixable: bool = Field(
        default=False,
        description="Whether this issue can be automatically repaired",
    )

    def model_post_init(self, __context: Any) -> None:
        if self.type and not self.issue_type:
            self.issue_type = self.type
        if not self.type and self.issue_type:
            self.type = str(self.issue_type)
        if self.description and not self.message:
            self.message = self.description
        if not self.description and self.message:
            self.description = self.message


class ValidationResult(BaseModel):
    """Result of a complete geometry QA pass.

    Matches the structure from plan Section 5, Workflow 7.
    """

    status: Literal["PASS", "FAIL"] = Field(
        default="PASS",
        description="Overall result: PASS or FAIL",
    )
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall geometric QA score")
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

    target: str = Field(default="", description="Object or area with the issue")
    problem: str = Field(default="", description="Description of the visual problem")
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
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Overall quality score from 0.0 (terrible) to 1.0 (perfect)",
    )
    overall_score: float = Field(default=0.9, ge=0.0, le=1.0)
    aesthetic_score: float = Field(default=0.9, ge=0.0, le=1.0)
    spec_compliance_score: float = Field(default=0.9, ge=0.0, le=1.0)
    approved: bool = Field(default=True)
    strengths: list[str] = Field(default_factory=list)
    issues: list[Any] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    iteration: int = Field(default=1, ge=1, description="Which critique iteration this is")
    max_iterations: int = Field(default=3, ge=1)
    recommendation: str = Field(
        default="",
        description="Overall recommendation: APPROVE, REVISE, or REJECT",
    )

    def model_post_init(self, __context: Any) -> None:
        if self.overall_score and not self.quality_score:
            self.quality_score = self.overall_score
        if not self.overall_score and self.quality_score:
            self.overall_score = self.quality_score
        if not self.recommendation:
            self.recommendation = "APPROVE" if self.approved else "REVISE"


class VisionReport(BaseModel):
    """Result of the Stage 11 Vision Critic pass."""
    
    object_presence: bool = Field(default=True, description="Whether the main object is present in the scene")
    required_component_presence: bool = Field(default=True, description="Whether all required sub-components are visible")
    color_match: bool = Field(default=True, description="Whether the colors align with the intent")
    approximate_shape_match: bool = Field(default=True, description="Whether the overall shape/silhouette is correct")
    obvious_visual_errors: list[str] = Field(default_factory=list, description="List of any glaring visual issues (e.g. floating geometry)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score of the visual critique")
    overall_result: Literal["PASS", "FAIL"] = Field(default="PASS", description="Overall validation result from the vision critic")



class QACheckResult(BaseModel):
    """A single deterministic geometry check result."""

    passed: bool
    severity: str  # critical, high, medium, low
    check_name: str
    object: str
    message: str
    suggested_action: str


class ValidationReport(BaseModel):
    """Final output of the deterministic geometry QA stage."""

    passed: bool = True
    checks: list[QACheckResult] = Field(default_factory=list)

