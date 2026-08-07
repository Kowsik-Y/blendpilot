"""
BlendPilot AI — LangGraph State Definition

Central typed state that flows through all workflow nodes.
Defined early so schemas can be used in Phase 1 tests.
"""

from __future__ import annotations

from typing import TypedDict


class BlendPilotState(TypedDict, total=False):
    """Central state passed through the LangGraph orchestrator.

    All fields are optional (total=False) so partial state updates work.
    This is defined in Phase 1 to establish the contract early, but
    won't be used by LangGraph until Phase 4.
    """

    project_id: str
    user_prompt: str
    reference_images: list[str]

    # Workflow 1 — Design Intent
    design_spec: dict | None

    # Workflow 2 — Scene Understanding
    scene_summary: dict | None

    # Workflow 3 — Research
    research_results: list[dict]

    # Workflow 4 — Planning
    design_plan: list[dict]
    current_step: int
    completed_steps: list[str]

    # Workflow 5 — Modeling
    created_objects: list[str]

    # Workflow 7 — Geometry QA
    geometry_issues: list[dict]
    geometry_score: float

    # Workflow 8 — Visual Critic
    visual_issues: list[dict]
    visual_score: float
    preview_image: str | None

    # Revision control
    revision_count: int
    max_revisions: int

    # Project management
    checkpoint_path: str | None

    # Workflow 9 — Human Feedback
    human_feedback: str | None
    approval_status: str | None

    # Workflow 10 — Export
    export_paths: list[str]

    # Error tracking
    errors: list[dict]
