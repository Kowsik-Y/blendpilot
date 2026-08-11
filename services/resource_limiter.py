"""
BlendPilot AI — Resource Limiter

Enforces resource limits per user workflow to prevent system overload:
- Memory usage: 4GB per workflow
- Scene complexity: 500K polygons (1M hard cap)
- Concurrent workflows: 1 per user
- Max runtime: 30 minutes per session
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger("blendpilot.services.resource_limiter")


class ResourceLimitError(Exception):
    """Raised when a resource limit is exceeded."""
    pass


class MemoryLimitExceeded(ResourceLimitError):
    """Raised when memory limit is exceeded."""
    pass


class PolycountLimitExceeded(ResourceLimitError):
    """Raised when polygon limit is exceeded."""
    pass


class ConcurrencyLimitExceeded(ResourceLimitError):
    """Raised when concurrent workflow limit is exceeded."""
    pass


class RuntimeLimitExceeded(ResourceLimitError):
    """Raised when max runtime is exceeded."""
    pass


class SceneComplexityExceeded(ResourceLimitError):
    """Raised when scene complexity exceeds hard limits."""
    pass


@dataclass
class ResourceUsage:
    """Tracks resource usage for a user workflow."""
    memory_gb: float = 0.0
    polycount: int = 0
    concurrent_workflows: int = 0
    runtime_minutes: float = 0.0
    created_at: datetime = None  # type: ignore
    started_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class ResourceLimiter:
    """
    Enforces resource limits for user workflows.

    Features:
    - Per-user resource isolation
    - Memory limit: 4GB per workflow
    - Polygon limit: 500K (soft), 1M (hard)
    - Concurrent workflows: 1 per user
    - Max runtime: 30 minutes per session
    """

    DEFAULT_MEMORY_LIMIT_GB = 4.0
    DEFAULT_POLYCOUNT_LIMIT = 500_000
    DEFAULT_POLYCOUNT_HARD_LIMIT = 1_000_000
    DEFAULT_MAX_CONCURRENT = 1
    DEFAULT_MAX_RUNTIME_MINUTES = 30

    def __init__(
        self,
        memory_limit_gb: float = DEFAULT_MEMORY_LIMIT_GB,
        polycount_limit: int = DEFAULT_POLYCOUNT_LIMIT,
        polycount_hard_limit: int = DEFAULT_POLYCOUNT_HARD_LIMIT,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        max_runtime_minutes: int = DEFAULT_MAX_RUNTIME_MINUTES,
    ):
        self.memory_limit_gb = memory_limit_gb
        self.polycount_limit = polycount_limit
        self.polycount_hard_limit = polycount_hard_limit
        self.max_concurrent = max_concurrent
        self.max_runtime_minutes = max_runtime_minutes

        self._user_resources: Dict[str, ResourceUsage] = {}
        self._lock = None  # Lazy initialization

    def _get_lock(self):
        """Get or create the asyncio lock."""
        import asyncio
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def check_resources(self, user_id: str) -> ResourceUsage:
        """
        Check if user has available resources.
        Raises appropriate exception if limits exceeded.
        """
        lock = self._get_lock()
        async with lock:
            usage = self._user_resources.get(user_id)

            if usage is None:
                # New user workflow
                usage = ResourceUsage(created_at=datetime.utcnow())
                self._user_resources[user_id] = usage

            # Check concurrent workflow limit
            if usage.concurrent_workflows >= self.max_concurrent:
                raise ConcurrencyLimitExceeded(
                    f"User {user_id} has {usage.concurrent_workflows} "
                    f"concurrent workflows (max: {self.max_concurrent})"
                )

            # Check memory limit
            if usage.memory_gb >= self.memory_limit_gb:
                raise MemoryLimitExceeded(
                    f"User {user_id} has used {usage.memory_gb:.1f}GB "
                    f"memory (limit: {self.memory_limit_gb}GB)"
                )

            # Check polygon limit
            if usage.polycount >= self.polycount_hard_limit:
                raise SceneComplexityExceeded(
                    f"Scene exceeds {self.polycount_hard_limit:,} polygon hard limit: "
                    f"{usage.polycount:,}"
                )

            return usage

    async def record_polycount(self, user_id: str, polycount: int) -> None:
        """Record polygon count for a user's workflow."""
        lock = self._get_lock()
        async with lock:
            usage = self._user_resources.get(user_id)
            if usage is None:
                usage = ResourceUsage(created_at=datetime.utcnow())
                self._user_resources[user_id] = usage

            usage.polycount = polycount

            # Warn if approaching soft limit
            if polycount > self.polycount_limit:
                logger.warning(
                    "User %s scene has %d polygons (soft limit: %d)",
                    user_id, polycount, self.polycount_limit
                )

    async def record_memory_usage(self, user_id: str, memory_gb: float) -> None:
        """Record memory usage for a user's workflow."""
        lock = self._get_lock()
        async with lock:
            usage = self._user_resources.get(user_id)
            if usage is None:
                usage = ResourceUsage(created_at=datetime.utcnow())
                self._user_resources[user_id] = usage

            usage.memory_gb = memory_gb

    async def start_workflow(self, user_id: str) -> None:
        """Mark a workflow as started for a user."""
        lock = self._get_lock()
        async with lock:
            usage = self._user_resources.get(user_id)
            if usage is None:
                usage = ResourceUsage(created_at=datetime.utcnow())
                self._user_resources[user_id] = usage

            usage.concurrent_workflows += 1
            if usage.started_at is None:
                usage.started_at = datetime.utcnow()

    async def end_workflow(self, user_id: str) -> None:
        """Mark a workflow as ended for a user."""
        lock = self._get_lock()
        async with lock:
            usage = self._user_resources.get(user_id)
            if usage is None:
                return

            if usage.concurrent_workflows > 0:
                usage.concurrent_workflows -= 1

            # Calculate runtime
            if usage.started_at:
                elapsed = datetime.utcnow() - usage.started_at
                usage.runtime_minutes = elapsed.total_seconds() / 60.0

    async def check_runtime_limit(self, user_id: str) -> None:
        """Check if user's workflow has exceeded max runtime."""
        lock = self._get_lock()
        async with lock:
            usage = self._user_resources.get(user_id)
            if usage is None or usage.started_at is None:
                return

            elapsed = datetime.utcnow() - usage.started_at
            runtime_minutes = elapsed.total_seconds() / 60.0

            if runtime_minutes > self.max_runtime_minutes:
                raise RuntimeLimitExceeded(
                    f"User {user_id} workflow exceeded {self.max_runtime_minutes}min limit: "
                    f"{runtime_minutes:.1f}min elapsed"
                )

    async def update_resource_usage(self, user_id: str, **kwargs) -> None:
        """Update resource usage fields."""
        lock = self._get_lock()
        async with lock:
            usage = self._user_resources.get(user_id)
            if usage is None:
                usage = ResourceUsage(created_at=datetime.utcnow())
                self._user_resources[user_id] = usage

            for key, value in kwargs.items():
                if hasattr(usage, key):
                    setattr(usage, key, value)

    async def get_user_resources(self, user_id: str) -> Optional[ResourceUsage]:
        """Get current resource usage for a user."""
        lock = self._get_lock()
        async with lock:
            return self._user_resources.get(user_id)

    async def get_all_users_usage(self) -> Dict[str, Dict[str, Any]]:
        """Get resource usage for all users."""
        lock = self._get_lock()
        async with lock:
            return {
                user_id: {
                    "memory_gb": usage.memory_gb,
                    "polycount": usage.polycount,
                    "concurrent_workflows": usage.concurrent_workflows,
                    "runtime_minutes": usage.runtime_minutes,
                    "created_at": usage.created_at.isoformat(),
                }
                for user_id, usage in self._user_resources.items()
            }

    async def cleanup_user(self, user_id: str) -> None:
        """Clean up user's resource records."""
        lock = self._get_lock()
        async with lock:
            if user_id in self._user_resources:
                del self._user_resources[user_id]

    async def clear_all(self) -> None:
        """Clear all resource records."""
        lock = self._get_lock()
        async with lock:
            self._user_resources.clear()
