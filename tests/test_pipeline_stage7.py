"""
BlendPilot AI — Stage 7: Synchronous Pipeline Integration Tests

Tests the full pipeline:
  IntentAgent → PlanningAgent → GenerationAgent → Blender Core

All tests run in mock_bpy mode (no real Blender needed).
"""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch

import pytest

from pipeline.sync_pipeline import run_sync_pipeline
from schemas.intent import IntentSpec
from schemas.pipeline import PipelineResult
from schemas.plan_state import ModelingPlan
from schemas.scene_state import SceneState


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _run(prompt: str, **kwargs) -> PipelineResult:
    """Run the pipeline in forced mock mode."""
    return await run_sync_pipeline(prompt, mock_mode=True, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — Full integration: red wooden table
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_synchronous_pipeline_integration(mock_bpy):
    """End-to-end: pipeline returns correct intent, plan, generation, scene, paths."""
    result = await _run("Create a red wooden table with four legs")

    # 1 — Intent
    assert isinstance(result.intent, IntentSpec)
    assert result.intent.object_type == "table"
    assert result.intent.color == "red"
    assert result.intent.material == "wood"

    # 2 — Plan
    assert isinstance(result.plan, ModelingPlan)
    assert len(result.plan.steps) > 3

    # 3 — Generation
    assert isinstance(result.generation, dict)
    assert result.generation["success"] is True
    assert len(result.generation["step_executions"]) > 0

    # 4 — SceneState (mock always returns a valid SceneState)
    assert result.scene_state is not None
    assert isinstance(result.scene_state, SceneState)

    # 5 — Deliverables
    assert result.success is True
    assert result.blend_path is not None and result.blend_path.endswith("table.blend")
    assert result.preview_path is not None and result.preview_path.endswith("preview.png")


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — PipelineResult is a typed Pydantic model
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_returns_typed_result(mock_bpy):
    """Pipeline must return a PipelineResult, not a raw dict."""
    result = await _run("Create a blue metal box")

    assert isinstance(result, PipelineResult)
    # All required fields must be populated
    assert result.intent is not None
    assert result.plan is not None
    assert result.generation is not None
    assert result.elapsed_seconds >= 0.0
    assert isinstance(result.report_lines, list)
    assert len(result.report_lines) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — Unsupported object raises ValueError
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_unsupported_object_raises(mock_bpy):
    """Pipeline must raise ValueError for unsupported object types."""
    with pytest.raises(ValueError, match="Unsupported object type"):
        await _run("Create a realistic dragon with wings")


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — Table plan has exactly 4 leg creation steps
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_plan_has_four_legs(mock_bpy):
    """Procedural table plan must contain exactly 4 leg create_primitive steps."""
    result = await _run("Create a red wooden table with four legs")

    leg_steps = [
        s for s in result.plan.steps
        if s.operation == "create_primitive" and s.target.startswith("leg_")
    ]
    assert len(leg_steps) == 4, f"Expected 4 leg steps, got {len(leg_steps)}"
    leg_names = {s.target for s in leg_steps}
    assert leg_names == {"leg_1", "leg_2", "leg_3", "leg_4"}


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — assign_material targets match create_primitive targets (bug check)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_assign_material_targets_match_create_primitive(mock_bpy):
    """Each assign_material step must reference an object that was actually created."""
    result = await _run("Create a wooden table")

    created_targets = {
        s.target for s in result.plan.steps if s.operation == "create_primitive"
    }
    assigned_targets = {
        s.target for s in result.plan.steps if s.operation == "assign_material"
    }

    # Every assigned target must correspond to a created object
    for target in assigned_targets:
        assert target in created_targets, (
            f"assign_material targets '{target}' which was never created. "
            f"Created objects: {created_targets}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 6 — Execution report contains all steps
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_report_contains_all_steps(mock_bpy):
    """Every executed step must appear in the report lines."""
    result = await _run("Create a green chair")

    step_executions = result.generation.get("step_executions", [])
    assert len(step_executions) > 0

    # Each step should have a corresponding [OK] or [FAIL] entry in report_lines
    report_text = "\n".join(result.report_lines)
    for se in step_executions:
        op = se.get("operation", "")
        # Report lines contain operation names
        assert op in report_text, f"Operation '{op}' not found in report"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7 — Elapsed time is tracked
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_execution_time_tracked(mock_bpy):
    """PipelineResult must record a non-negative elapsed time."""
    result = await _run("Create a wooden stool")

    assert result.elapsed_seconds >= 0.0
    # Report should mention elapsed time
    elapsed_in_report = any("Elapsed" in line for line in result.report_lines)
    assert elapsed_in_report, "Report should include an 'Elapsed' line"


# ─────────────────────────────────────────────────────────────────────────────
# Test 8 — CLI smoke test (subprocess, --mock flag)
# ─────────────────────────────────────────────────────────────────────────────

def test_cli_smoke_mock_mode():
    """CLI must exit 0 and print a report when run with --mock."""
    result = subprocess.run(
        [sys.executable, "cli.py", "Create a red wooden table with four legs", "--mock"],
        capture_output=True,
        text=True,
        cwd=".",  # Run from project root
    )
    assert result.returncode == 0, (
        f"CLI exited with code {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    assert "SUCCESS" in result.stdout or "OK" in result.stdout, (
        f"Expected 'SUCCESS' or 'OK' in CLI output.\nSTDOUT:\n{result.stdout}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 9 — CLI error exit for unsupported object
# ─────────────────────────────────────────────────────────────────────────────

def test_cli_unsupported_object_exits_nonzero():
    """CLI must exit non-zero for an unsupported object type."""
    result = subprocess.run(
        [sys.executable, "cli.py", "Create a realistic dragon", "--mock"],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert result.returncode != 0, (
        "CLI should exit non-zero for unsupported object types."
    )
