"""
BlendPilot AI — LangGraph Conditional Routing

Routing for the Decision Agent's self-repair loop.
The single conditional edge (route_after_decision) replaces the three
legacy route functions (route_after_geometry_qa, route_after_visual_critic,
route_after_human_feedback).
"""

from __future__ import annotations

import logging
from typing import Literal

from graph.state import BlendPilotState

logger = logging.getLogger("blendpilot.graph.routes")


def route_after_decision(
    state: BlendPilotState,
) -> Literal["repair", "export"]:
    """Route based on the Decision Agent's verdict.

    - "APPROVE" → export
    - "REPAIR"  → repair (loops back through Scene State after)
    """
    decision = state.get("decision", "APPROVE")

    if decision == "REPAIR":
        priority = state.get("priority_issue", "geometry")
        logger.info("[Route] Decision=REPAIR (priority: %s) → repair", priority)
        return "repair"

    logger.info("[Route] Decision=APPROVE → export")
    return "export"
