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

    # ── Geometry QA ──────────────────────────────────────────────────────
    geometry_qa_status: str   # PASS, FAIL, PENDING
    geometry_score: float
    geometry_issues: list[dict[str, Any]]

    # ── Visual Critic ─────────────────────────────────────────────────────
    visual_qa_approved: bool
    visual_score: float
    visual_issues: list[str]

    # ── Decision Agent ────────────────────────────────────────────────────
    decision: str             # APPROVE, REPAIR
    decision_reason: str
    priority_issue: str       # geometry, visual, none

    # ── Repair Agent ──────────────────────────────────────────────────────
    geometry_repair_count: int
    max_geometry_repairs: int
    visual_revision_count: int
    max_visual_revisions: int

    # ── Export ────────────────────────────────────────────────────────────
    export_directory: str | None
    exported_files: list[str]
    asset_report: dict[str, Any] | None

    # ── Event Log ─────────────────────────────────────────────────────────
    events: list[dict[str, Any]]
    checkpoint_path: str | None

    # ── Stage 8 LangGraph Orchestration Additions ───────────────────────────
    intent: dict[str, Any] | None
    plan: dict[str, Any] | None
    executable_operations: list[dict[str, Any]]
    execution_result: dict[str, Any] | None
    scene_state: dict[str, Any] | None
    errors: list[str]
    iteration_count: int


def create_initial_state(
    user_prompt: str,
    project_id: str | None = None,
    session_id: str | None = None,
    reference_images: list[str] | None = None,
    api_key: str | None = None,
    provider: str | None = None,
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
        "geometry_qa_status": "PENDING",
        "geometry_score": 1.0,
        "geometry_issues": [],
        # Visual Critic
        "visual_qa_approved": False,
        "visual_score": 0.0,
        "visual_issues": [],
        # Decision
        "decision": "REPAIR",
        "decision_reason": "",
        "priority_issue": "none",
        # Repair counters
        "geometry_repair_count": 0,
        "max_geometry_repairs": 3,
        "visual_revision_count": 0,
        "max_visual_revisions": 3,
        # Export
        "export_directory": None,
        "exported_files": [],
        "asset_report": None,
        # Events
        "events": [],
        "checkpoint_path": None,
        # Stage 8 Orchestration Additions
        "intent": None,
        "plan": None,
        "executable_operations": [],
        "execution_result": None,
        "scene_state": None,
        "errors": [],
        "iteration_count": 0,
    }

    if overrides:
        state.update(overrides)  # type: ignore

    return state
