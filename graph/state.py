"""
BlendPilot AI — LangGraph Typed State Definition

Defines the central state dictionary that flows across all agent nodes,
supporting serialization, checkpointing, and conditional branch routing.

Target pipeline:
    User → Intent → Planning → Generation → Scene State →
    Geometry QA → Visual Critic → Decision → Repair → Re-validation → Export
"""

from __future__ import annotations

import uuid
from typing import Any, TypedDict


class AgentStepEvent(TypedDict, total=False):
    """Event representing an agent's incremental progress update for SSE streaming."""
    timestamp: str
    agent_name: str
    step_description: str
    status: str  # STARTING, RUNNING, COMPLETED, FAILED
    details: dict[str, Any]


class BlendPilotState(TypedDict, total=False):
    """Central state passed through the LangGraph multi-agent orchestrator."""

    # ── Session & Identity ────────────────────────────────────────────────
    project_id: str
    session_id: str
    user_prompt: str
    reference_images: list[str]
    current_agent: str
    status: str  # IDLE, RUNNING, COMPLETED, FAILED
    error: str | None

    # ── Config ────────────────────────────────────────────────────────────
    api_key: str | None
    provider: str | None
    baseline_mode: bool

    # ── Intent Agent ─────────────────────────────────────────────────────
    design_spec: dict[str, Any] | None

    # ── Planning Agent ───────────────────────────────────────────────────
    design_plan: dict[str, Any] | None

    # ── Generation Agent ─────────────────────────────────────────────────
    created_objects: list[str]
    materials_created: list[str]
    modeling_logs: list[dict[str, Any]]
    preview_image_path: str | None

    # ── Scene State (post-generation Blender context snapshot) ───────────
    scene_summary: dict[str, Any] | None

    # ── Geometry QA (Stage 9) ────────────────────────────────────────────
    validation_report: dict[str, Any] | None

    # ── Vision Critic (Stage 11) ─────────────────────────────────────────
    vision_report: dict[str, Any] | None



    # ── Event Log ─────────────────────────────────────────────────────────
    events: list[dict[str, Any]]
    checkpoint_path: str | None

    # ── Stage 8 LangGraph Orchestration Additions ───────────────────────────
    intent: dict[str, Any] | None
    plan: dict[str, Any] | None
    executable_operations: list[dict[str, Any]]
    execution_result: dict[str, Any] | None
    scene_state: dict[str, Any] | None
    repair_plan: dict[str, Any] | None
    errors: list[str]
    iteration_count: int
    max_iterations: int


def create_initial_state(
    user_prompt: str,
    project_id: str | None = None,
    session_id: str | None = None,
    reference_images: list[str] | None = None,
    api_key: str | None = None,
    provider: str | None = None,
    baseline_mode: bool = False,
    overrides: dict[str, Any] | None = None,
) -> BlendPilotState:
    """Create a fully initialized default state for starting a modeling pipeline."""
    pid = project_id or f"proj_{uuid.uuid4().hex[:8]}"
    sid = session_id or f"sess_{uuid.uuid4().hex[:8]}"

    state: BlendPilotState = {
        # Identity
        "project_id": pid,
        "session_id": sid,
        "user_prompt": user_prompt,
        "reference_images": reference_images or [],
        "current_agent": "intent_agent",
        "status": "RUNNING",
        "error": None,
        # Config
        "api_key": api_key,
        "provider": provider or "openai",
        "baseline_mode": baseline_mode,
        # Intent
        "design_spec": None,
        # Planning
        "design_plan": None,
        # Generation
        "created_objects": [],
        "materials_created": [],
        "modeling_logs": [],
        "preview_image_path": None,
        # Scene State
        "scene_summary": None,
        # Geometry QA
        "validation_report": None,

        # Events
        "events": [],
        "checkpoint_path": None,
        # Stage 8 Orchestration Additions
        "intent": None,
        "plan": None,
        "executable_operations": [],
        "execution_result": None,
        "scene_state": None,
        "repair_plan": None,
        "errors": [],
        "iteration_count": 0,
        "max_iterations": 3,
    }

    if overrides:
        state.update(overrides)  # type: ignore

    return state
