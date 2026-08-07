"""
BlendPilot AI — LangGraph State Checkpointing & Persistence

Provides checkpointer configuration for session state storage and human-in-the-loop rollback.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger("blendpilot.graph.persistence")


def get_checkpointer() -> MemorySaver:
    """Return an in-memory checkpointer for LangGraph session state storage."""
    logger.info("Initializing LangGraph MemorySaver checkpointer")
    return MemorySaver()
