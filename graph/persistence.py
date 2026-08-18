"""
BlendPilot — LangGraph State Checkpointing & Persistence

Provides checkpointer configuration for session state storage and human-in-the-loop rollback.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from contextlib import contextmanager

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

logger = logging.getLogger("blendpilot.graph.persistence")


def get_checkpointer():
    """Return a Postgres checkpointer for LangGraph durable session state storage."""
    logger.info("Initializing LangGraph PostgresSaver checkpointer")
    # For a real async setup we would use AsyncPostgresSaver and AsyncConnectionPool,
    # but based on current API, returning a configured PostgresSaver object is requested.
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://user:password@localhost:5432/blendpilot")

    # We would normally yield this or manage the pool at application startup.
    # To keep the API similar, we return a ContextManager or require the caller to manage the pool.
    # Here we simplify by returning the saver setup block.
    pool = ConnectionPool(conninfo=db_url)
    return PostgresSaver(pool)
