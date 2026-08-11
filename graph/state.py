"""
BlendPilot AI — LangGraph Typed State Definition

Defines the central state dictionary that flows across all 10 agent nodes,
supporting serialization, checkpointing, and conditional branch routing.
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

    # Session & Identity
    project_id: str
    session_id: str
    user_prompt: str
    enhanced_prompt: str | None
    reference_images: list[str]
    current_agent: str
    status: str  # IDLE, RUNNING, INTERRUPTED, COMPLETED, FAILED
    error: str | None

    # Config
    api_key: str | None
    provider: str | None
    model: str | None
    base_url: str | None
    temperature: float
    max_tokens: int
    context_window_size: int
    rag_enabled: bool
    rag_top_k: int
    blender_mock_mode: bool

    # Workflow 1 — Design Intent
    design_spec: dict[str, Any] | None

    # Workflow 2 — Scene Understanding
    scene_summary: dict[str, Any] | None

    # Workflow 3 — Reference & Technical Research
    research_results: list[dict[str, Any]]

    # Workflow 4 — Design Planning
    design_plan: dict[str, Any] | None
    current_step_index: int
    completed_steps: list[str]

    # Workflow 5 — Autonomous Modeling
    created_objects: list[str]
    modeling_logs: list[dict[str, Any]]

    # Workflow 6 — Materials & Lighting
    materials_created: list[str]
    preview_image_path: str | None

    # Workflow 7 — Deterministic Geometry QA & Repair
    geometry_qa_status: str  # PASS, FAIL
    geometry_score: float
    geometry_issues: list[dict[str, Any]]
    geometry_repair_count: int
    max_geometry_repairs: int

    # Workflow 8 — Visual Critic & Aesthetic Self-Repair
    visual_qa_approved: bool
    visual_score: float
    visual_issues: list[str]
    visual_revision_count: int
    max_visual_revisions: int

    # Workflow 9 — Human Review & Feedback
    human_feedback: str | None
    human_action: str | None  # APPROVE, REQUEST_CHANGE, ROLLBACK, REJECT
    approval_status: str  # PENDING, APPROVED, REVISION_REQUESTED

    # Workflow 10 — Production Export & Packaging
    export_directory: str | None
    exported_files: list[str]
    asset_report: dict[str, Any] | None

    # Stream Events & Logs
    events: list[dict[str, Any]]
    stream_events: list[dict[str, Any]]
    stream_event_seq: int
    checkpoint_path: str | None


def create_initial_state(
    user_prompt: str,
    project_id: str | None = None,
    session_id: str | None = None,
    reference_images: list[str] | None = None,
    overrides: dict[str, Any] | None = None,
) -> BlendPilotState:
    """Create a fully initialized default state for starting a modeling pipeline."""
    pid = project_id or f"proj_{uuid.uuid4().hex[:8]}"
    sid = session_id or f"sess_{uuid.uuid4().hex[:8]}"

    state: BlendPilotState = {
        "project_id": pid,
        "session_id": sid,
        "user_prompt": user_prompt,
        "enhanced_prompt": None,
        "reference_images": reference_images or [],
        "current_agent": "intent_agent",
        "status": "RUNNING",
        "error": None,
        "api_key": None,
        "provider": None,
        "model": None,
        "base_url": None,
        "temperature": 0.0,
        "max_tokens": 4096,
        "context_window_size": 128000,
        "rag_enabled": True,
        "rag_top_k": 4,
        "blender_mock_mode": False,
        "design_spec": None,
        "scene_summary": None,
        "research_results": [],
        "design_plan": None,
        "current_step_index": 0,
        "completed_steps": [],
        "created_objects": [],
        "modeling_logs": [],
        "materials_created": [],
        "preview_image_path": None,
        "geometry_qa_status": "PENDING",
        "geometry_score": 1.0,
        "geometry_issues": [],
        "geometry_repair_count": 0,
        "max_geometry_repairs": 3,
        "visual_qa_approved": False,
        "visual_score": 0.0,
        "visual_issues": [],
        "visual_revision_count": 0,
        "max_visual_revisions": 3,
        "human_feedback": None,
        "human_action": None,
        "approval_status": "PENDING",
        "export_directory": None,
        "exported_files": [],
        "asset_report": None,
        "events": [],
        "stream_events": [],
        "stream_event_seq": 0,
        "checkpoint_path": None,
    }

    if overrides:
        state.update(overrides)  # type: ignore

    return state
