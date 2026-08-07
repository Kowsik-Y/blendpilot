"""
BlendPilot AI — LangGraph Conditional Routing

Defines routing conditions for self-repair loops, quality thresholds, and human review decisions.
"""

from __future__ import annotations

import logging
from typing import Literal

from graph.state import BlendPilotState

logger = logging.getLogger("blendpilot.graph.routes")


def route_after_geometry_qa(
    state: BlendPilotState,
) -> Literal["visual_critic", "geometry_repair"]:
    """Route based on deterministic Geometry QA result and maximum repair iterations."""
    status = state.get("geometry_qa_status", "PASS")
    repair_count = state.get("geometry_repair_count", 0)
    max_repairs = state.get("max_geometry_repairs", 3)

    if status == "PASS" or repair_count >= max_repairs:
        logger.info("[Route] Geometry QA passed or max repairs reached (%d/%d) -> visual_critic", repair_count, max_repairs)
        return "visual_critic"

    logger.info("[Route] Geometry QA failed -> triggering geometry_repair loop (attempt %d/%d)", repair_count + 1, max_repairs)
    return "geometry_repair"


def route_after_visual_critic(
    state: BlendPilotState,
) -> Literal["human_feedback", "visual_repair"]:
    """Route based on visual critique score and maximum aesthetic revision count."""
    approved = state.get("visual_qa_approved", True)
    rev_count = state.get("visual_revision_count", 0)
    max_revs = state.get("max_visual_revisions", 3)

    if approved or rev_count >= max_revs:
        logger.info("[Route] Visual critique approved or max revisions reached (%d/%d) -> human_feedback", rev_count, max_revs)
        return "human_feedback"

    logger.info("[Route] Visual critique requires aesthetic refinement -> visual_repair (attempt %d/%d)", rev_count + 1, max_revs)
    return "visual_repair"


def route_after_human_feedback(
    state: BlendPilotState,
) -> Literal["export", "planning"]:
    """Route based on human review approval or revision request."""
    status = state.get("approval_status", "APPROVED")

    if status == "APPROVED":
        logger.info("[Route] Human review approved -> export")
        return "export"

    logger.info("[Route] Human requested changes -> planning")
    return "planning"
