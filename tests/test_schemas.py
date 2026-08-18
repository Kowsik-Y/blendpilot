"""
BlendPilot — Schema Tests

Tests for Pydantic models that can run entirely outside Blender.
"""

from __future__ import annotations

import pytest

from schemas.design import DesignSpec, Dimensions
from schemas.plan import DesignPlan, PlanStep, StepStatus
from schemas.scene import MeshStatistics, ObjectInfo, ObjectType, SceneSummary
from schemas.validation import (
    IssueType,
    Severity,
    ValidationIssue,
    ValidationResult,
    VisualCritiqueIssue,
    VisualCritiqueResult,
)


# ── Design Schemas ──────────────────────────────────────────────


class TestDimensions:
    def test_valid_dimensions(self):
        d = Dimensions(width=1.0, depth=0.7, height=0.6)
        assert d.width == 1.0
        assert d.depth == 0.7
        assert d.height == 0.6

    def test_zero_dimension_rejected(self):
        with pytest.raises(Exception):
            Dimensions(width=0, depth=0.7, height=0.6)

    def test_negative_dimension_rejected(self):
        with pytest.raises(Exception):
            Dimensions(width=-1.0, depth=0.7, height=0.6)


class TestDesignSpec:
    def test_full_spec(self):
        spec = DesignSpec(
            asset_type="sci-fi crate",
            style="low-poly",
            dimensions=Dimensions(width=1.0, depth=0.7, height=0.6),
            triangle_limit=8000,
            target_platform="Unity",
            materials=["dark metal", "blue emissive strips"],
            export_format="FBX",
        )
        assert spec.asset_type == "sci-fi crate"
        assert spec.triangle_limit == 8000
        assert len(spec.materials) == 2

    def test_defaults(self):
        spec = DesignSpec(
            asset_type="table",
            dimensions=Dimensions(width=1.2, depth=0.8, height=0.75),
        )
        assert spec.style == "low-poly"
        assert spec.target_platform == "Unity"
        assert spec.export_format == "FBX"
        assert spec.materials == []

    def test_empty_asset_type_rejected(self):
        with pytest.raises(Exception):
            DesignSpec(
                asset_type="",
                dimensions=Dimensions(width=1.0, depth=1.0, height=1.0),
            )

    def test_negative_triangle_limit_rejected(self):
        with pytest.raises(Exception):
            DesignSpec(
                asset_type="crate",
                dimensions=Dimensions(width=1.0, depth=1.0, height=1.0),
                triangle_limit=-100,
            )

    def test_json_roundtrip(self):
        spec = DesignSpec(
            asset_type="barrel",
            dimensions=Dimensions(width=0.5, depth=0.5, height=0.8),
            materials=["wood", "metal bands"],
        )
        json_str = spec.model_dump_json()
        restored = DesignSpec.model_validate_json(json_str)
        assert restored.asset_type == spec.asset_type
        assert restored.dimensions.height == spec.dimensions.height


# ── Scene Schemas ───────────────────────────────────────────────


class TestObjectInfo:
    def test_mesh_object(self):
        obj = ObjectInfo(
            name="CrateBody",
            object_type=ObjectType.MESH,
            dimensions=(1.0, 0.7, 0.6),
        )
        assert obj.name == "CrateBody"
        assert obj.object_type == ObjectType.MESH
        assert obj.visible is True

    def test_camera_object(self):
        obj = ObjectInfo(
            name="Camera",
            object_type=ObjectType.CAMERA,
        )
        assert obj.object_type == ObjectType.CAMERA


class TestSceneSummary:
    def test_empty_scene(self):
        summary = SceneSummary()
        assert summary.object_count == 0
        assert summary.objects == []
        assert summary.has_camera is False

    def test_populated_scene(self):
        summary = SceneSummary(
            object_count=3,
            objects=[
                ObjectInfo(name="Cube", object_type=ObjectType.MESH),
                ObjectInfo(name="Camera", object_type=ObjectType.CAMERA),
                ObjectInfo(name="Light", object_type=ObjectType.LIGHT),
            ],
            has_camera=True,
            has_lights=True,
            active_object="Cube",
        )
        assert summary.object_count == 3
        assert summary.has_camera is True


class TestMeshStatistics:
    def test_basic_stats(self):
        stats = MeshStatistics(
            object_name="Cube",
            vertex_count=8,
            edge_count=12,
            face_count=6,
            triangle_count=12,
        )
        assert stats.vertex_count == 8
        assert stats.triangle_count == 12


# ── Plan Schemas ────────────────────────────────────────────────


class TestPlanStep:
    def test_pending_step(self):
        step = PlanStep(
            step_id=1,
            action="Create main crate body",
            target_object="CrateBody",
            required_tool="create_primitive",
        )
        assert step.status == StepStatus.PENDING
        assert step.dependencies == []

    def test_step_with_dependencies(self):
        step = PlanStep(
            step_id=3,
            action="Add bevel modifier",
            target_object="CrateBody",
            required_tool="add_modifier",
            dependencies=[1, 2],
        )
        assert step.dependencies == [1, 2]


class TestDesignPlan:
    def test_plan_completion(self):
        plan = DesignPlan(
            plan_id="test-001",
            asset_type="crate",
            steps=[
                PlanStep(step_id=1, action="Create body",
                         status=StepStatus.COMPLETED),
                PlanStep(step_id=2, action="Add modifier",
                         status=StepStatus.COMPLETED),
            ],
            total_steps=2,
            completed_count=2,
        )
        assert plan.is_complete is True
        assert plan.current_step is None

    def test_plan_in_progress(self):
        plan = DesignPlan(
            plan_id="test-002",
            asset_type="table",
            steps=[
                PlanStep(step_id=1, action="Create top",
                         status=StepStatus.COMPLETED),
                PlanStep(step_id=2, action="Create legs",
                         status=StepStatus.PENDING),
                PlanStep(step_id=3, action="Add material",
                         status=StepStatus.PENDING),
            ],
            total_steps=3,
            completed_count=1,
        )
        assert plan.is_complete is False
        assert plan.current_step is not None
        assert plan.current_step.step_id == 2


# ── Validation Schemas ──────────────────────────────────────────


class TestValidationResult:
    def test_passing_result(self):
        result = ValidationResult(
            status="PASS",
            object_name="CrateBody",
            triangle_count=6000,
            triangle_limit=8000,
        )
        assert result.status == "PASS"
        assert result.has_critical_issues is False

    def test_failing_result(self):
        result = ValidationResult(
            status="FAIL",
            object_name="CrateBody",
            triangle_count=6425,
            triangle_limit=8000,
            issues=[
                ValidationIssue(
                    issue_type=IssueType.UNAPPLIED_TRANSFORM,
                    object_name="CrateBody",
                    severity=Severity.MEDIUM,
                    message="Scale is not applied",
                    auto_fixable=True,
                ),
            ],
        )
        assert result.status == "FAIL"
        assert len(result.issues) == 1
        assert result.auto_fixable_count == 1

    def test_critical_issues(self):
        result = ValidationResult(
            status="FAIL",
            object_name="Broken",
            issues=[
                ValidationIssue(
                    issue_type=IssueType.NON_MANIFOLD,
                    object_name="Broken",
                    severity=Severity.CRITICAL,
                ),
            ],
        )
        assert result.has_critical_issues is True

    def test_invalid_status_rejected(self):
        with pytest.raises(Exception):
            ValidationResult(status="MAYBE", object_name="X")


class TestVisualCritiqueResult:
    def test_good_critique(self):
        result = VisualCritiqueResult(
            quality_score=0.92,
            recommendation="APPROVE",
        )
        assert result.quality_score == 0.92
        assert result.issues == []

    def test_critique_with_issues(self):
        result = VisualCritiqueResult(
            quality_score=0.65,
            issues=[
                VisualCritiqueIssue(
                    target="LeftGlowStrip",
                    problem="not symmetrical",
                    severity=Severity.HIGH,
                    recommended_change="align with right-side strip",
                ),
            ],
            recommendation="REVISE",
        )
        assert len(result.issues) == 1
        assert result.quality_score == 0.65

    def test_score_bounds(self):
        with pytest.raises(Exception):
            VisualCritiqueResult(quality_score=1.5)
        with pytest.raises(Exception):
            VisualCritiqueResult(quality_score=-0.1)
