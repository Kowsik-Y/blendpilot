"""
BlendPilot AI — Stage 7: Synchronous Pipeline

Connects:
  IntentAgent → PlanningAgent → GenerationAgent → Blender Core

into one clean synchronous pipeline (no LangGraph).

Usage (from Python):
    from pipeline.sync_pipeline import run_sync_pipeline
    result = await run_sync_pipeline("Create a red wooden table")

Usage (CLI):
    python cli.py "Create a red wooden table with four legs"
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from agents.intent_agent import IntentAgent
from agents.planning_agent import PlanningAgent
from agents.generation_agent import GenerationAgent
from schemas.pipeline import PipelineResult

logger = logging.getLogger("blendpilot.pipeline.sync")


def _detect_bpy() -> bool:
    """Return True if bpy (Blender Python API) is importable."""
    try:
        import bpy  # noqa: F401
        return True
    except ImportError:
        return False


async def run_sync_pipeline(
    prompt: str,
    output_dir: str | None = None,
    mock_mode: bool | None = None,
    verbose: bool = False,
) -> PipelineResult:
    """Execute the Stage 7 synchronous pipeline end-to-end.

    Steps:
        1. Parse intent       — IntentAgent extracts structured IntentSpec
        2. Generate plan      — PlanningAgent builds ModelingPlan
        3. Execute operations — GenerationAgent runs plan steps via Blender core
        4. Save .blend scene  — core.project.save_project()
        5. Render preview     — core.rendering.render_preview()
        6. Collect SceneState — core.scene_inspector.inspect_scene()
        7. Build report       — assemble human-readable execution report

    Args:
        prompt:     Natural-language description of the 3D asset to create.
        output_dir: Directory for output files. Defaults to ``output/<obj_type>/``.
        mock_mode:  If True, skip real Blender calls. If None, auto-detects bpy.
        verbose:    If True, emit detailed logging.

    Returns:
        PipelineResult with all pipeline outputs and execution metadata.

    Raises:
        ValueError: If the requested object type is unsupported.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    start_time = time.perf_counter()
    report_lines: list[str] = []

    def _log(msg: str) -> None:
        report_lines.append(msg)
        logger.info(msg)

    # ------------------------------------------------------------------
    # Stage 1 — Parse Intent
    # ------------------------------------------------------------------
    _log(f"[1/6] Parsing design intent for: {prompt!r}")
    intent_agent = IntentAgent()
    intent = await intent_agent.execute(user_prompt=prompt)
    _log(f"      category={intent.object_type}  style={intent.style}  "
         f"color={intent.color or 'default'}  material={intent.material or 'default'}")

    obj_type = intent.object_type
    effective_output_dir = output_dir or os.path.join("output", obj_type)
    os.makedirs(effective_output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Stage 2 — Generate Modeling Plan
    # ------------------------------------------------------------------
    _log("[2/6] Generating modeling plan...")
    planning_agent = PlanningAgent()
    plan = await planning_agent.execute(intent=intent)
    _log(f"      {len(plan.steps)} modeling steps generated")

    # ------------------------------------------------------------------
    # Stage 3 — Execute Supported Operations
    # ------------------------------------------------------------------
    _log("[3/6] Executing modeling operations...")
    use_mock = mock_mode if mock_mode is not None else (not _detect_bpy())
    generation_agent = GenerationAgent(mock_mode=use_mock)
    output_image_path = os.path.join(effective_output_dir, "preview.png")
    gen_result: dict[str, Any] = await generation_agent.execute(
        spec=intent,
        plan=plan,
        output_image_path=output_image_path,
    )
    step_executions = gen_result.get("step_executions", [])
    success_count = sum(1 for s in step_executions if s.get("success"))
    _log(f"      {success_count}/{len(plan.steps)} steps succeeded")
    for se in step_executions:
        status = "OK" if se.get("success") else "FAIL"
        _log(f"      [{status}] step {se.get('step_id')}: {se.get('operation')} -> {se.get('target')}")

    # ------------------------------------------------------------------
    # Stage 4 — Save Blender Scene
    # ------------------------------------------------------------------
    blend_path: str | None = None
    _log("[4/6] Saving Blender scene...")
    if not use_mock:
        try:
            import core.project
            blend_path = os.path.abspath(
                os.path.join(effective_output_dir, f"{obj_type}.blend")
            )
            save_res = core.project.save_project(path=blend_path)
            if save_res.get("success"):
                _log(f"      Saved .blend -> {blend_path}")
            else:
                _log(f"      Save failed: {save_res.get('message')}")
                blend_path = None
        except Exception as exc:
            _log(f"      Save skipped: {exc}")
    else:
        blend_path = os.path.abspath(
            os.path.join(effective_output_dir, f"{obj_type}.blend")
        )
        _log(f"      [mock] Would save -> {blend_path}")

    # ------------------------------------------------------------------
    # Stage 5 — Render Preview
    # ------------------------------------------------------------------
    preview_path: str | None = None
    _log("[5/6] Rendering preview...")
    if not use_mock:
        try:
            import core.rendering
            preview_path = os.path.abspath(output_image_path)
            render_res = core.rendering.render_preview(
                output_path=preview_path,
                resolution_x=512,
                resolution_y=512,
                samples=16,
            )
            if render_res.get("success"):
                _log(f"      Rendered preview -> {preview_path}")
            else:
                _log(f"      Render failed: {render_res.get('message')}")
                preview_path = None
        except Exception as exc:
            _log(f"      Render skipped: {exc}")
    else:
        preview_path = os.path.abspath(output_image_path)
        _log(f"      [mock] Would render -> {preview_path}")

    # ------------------------------------------------------------------
    # Stage 6 — Collect SceneState
    # ------------------------------------------------------------------
    from schemas.scene_state import SceneState
    scene_state: SceneState | None = None
    _log("[6/6] Collecting SceneState...")
    if not use_mock:
        try:
            from core.scene_inspector import inspect_scene
            scene_state = inspect_scene(user_prompt=prompt)
            obj_count = len(scene_state.objects)
            _log(f"      Scene: {obj_count} objects, {scene_state.total_triangle_count} tris")
        except Exception as exc:
            _log(f"      Inspection skipped: {exc}")
    else:
        # Build a minimal mock SceneState so consumers always get a typed value
        from schemas.scene_state import SceneStatus
        scene_state = SceneState(
            status=SceneStatus.GENERATED,
            user_prompt=prompt,
            objects=[],
            materials=[],
            lighting=[],
        )
        _log("      [mock] Returning empty SceneState")

    # ------------------------------------------------------------------
    # Stage 7 — Build Report
    # ------------------------------------------------------------------
    elapsed = time.perf_counter() - start_time
    overall_success = bool(gen_result.get("success", False))

    report_lines.extend([
        "=" * 60,
        "             PIPELINE EXECUTION REPORT",
        "=" * 60,
        f" Prompt:          {prompt}",
        f" Object Type:     {intent.object_type}",
        f" Color:           {intent.color or 'default'}",
        f" Material:        {intent.material or 'default'}",
        f" Steps:           {success_count}/{len(plan.steps)} succeeded",
        f" Blend File:      {blend_path or 'N/A'}",
        f" Preview Image:   {preview_path or 'N/A'}",
        f" Elapsed:         {elapsed:.3f}s",
        f" Status:          {'SUCCESS' if overall_success else 'FAILED'}",
        "=" * 60,
    ])

    return PipelineResult(
        intent=intent,
        plan=plan,
        generation=gen_result,
        scene_state=scene_state,
        blend_path=blend_path,
        preview_path=preview_path,
        success=overall_success,
        elapsed_seconds=elapsed,
        report_lines=report_lines,
    )
