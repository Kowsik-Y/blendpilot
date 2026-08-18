"""
BlendPilot — Mode Manager

Manages execution mode (live/simulated) with:
- Live-to-simulated mode switching detection
- Graceful fallback when Blender connection is lost
- Mode change notifications streamed to clients
- Context preservation during mode switch
- Logging of connection loss events
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from services.streaming import StreamingOrchestrator

logger = logging.getLogger("blendpilot.core.mode_manager")


class ExecutionMode(str, Enum):
    """Available execution modes."""
    LIVE = "live"
    SIMULATED = "simulated"


@dataclass
class ModeChangeEvent:
    """Event for mode change."""
    from_mode: ExecutionMode
    to_mode: ExecutionMode
    reason: str
    timestamp: datetime
    agents_affected: list[str]


class ModeManager:
    """
    Manages execution mode switching between live and simulated modes.

    Features:
    - Live-to-simulated fallback on connection loss
    - Mode change notifications
    - Context preservation
    - Connection health monitoring
    """

    def __init__(
        self,
        streaming: Optional[StreamingOrchestrator] = None,
        health_check_fn: Optional[Callable[[], bool]] = None,
    ):
        self.streaming = streaming
        self.health_check_fn = health_check_fn

        self._current_mode = ExecutionMode.SIMULATED
        self._connection_established = False
        self._mode_change_callbacks: list[Callable[[
            ModeChangeEvent], Any]] = []
        self._health_check_interval = 5.0  # seconds
        self._last_health_check = 0.0
        self._health_check_failures = 0
        self._max_health_failures = 3

    def register_mode_change_callback(
        self,
        callback: Callable[[ModeChangeEvent], Any],
    ) -> None:
        """Register a callback for mode changes."""
        self._mode_change_callbacks.append(callback)

    async def _emit_mode_change(
        self,
        from_mode: ExecutionMode,
        to_mode: ExecutionMode,
        reason: str,
        agents_affected: Optional[list[str]] = None,
    ) -> None:
        """Emit mode change event to streaming."""
        event = ModeChangeEvent(
            from_mode=from_mode,
            to_mode=to_mode,
            reason=reason,
            timestamp=datetime.utcnow(),
            agents_affected=agents_affected or [],
        )

        if self.streaming:
            try:
                await self.streaming.broadcast("mode_change", {
                    "from_mode": from_mode.value,
                    "to_mode": to_mode.value,
                    "reason": reason,
                    "timestamp": event.timestamp.isoformat(),
                    "agents_affected": event.agents_affected,
                })
            except Exception as e:
                logger.warning("Failed to emit mode change: %s", e)

        for callback in self._mode_change_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.warning("Mode change callback failed: %s", e)

    async def set_mode(
        self,
        mode: ExecutionMode,
        reason: str = "Manual mode change",
    ) -> None:
        """Set the execution mode."""
        if mode == self._current_mode:
            return

        from_mode = self._current_mode
        self._current_mode = mode

        logger.info("Mode changed from %s to %s: %s",
                    from_mode.value, mode.value, reason)

        await self._emit_mode_change(
            from_mode=from_mode,
            to_mode=mode,
            reason=reason,
        )

    async def check_connection_health(self) -> bool:
        """Check if live connection is still healthy."""
        current_time = datetime.utcnow().timestamp()

        if self.health_check_fn:
            try:
                is_healthy = self.health_check_fn()
                self._connection_established = is_healthy
                return is_healthy
            except Exception as e:
                logger.warning("Health check failed: %s", e)
                self._connection_established = False
                return False

        # Default: assume healthy if not connected
        return self._connection_established

    async def monitor_connection(
        self,
        current_mode: ExecutionMode,
        agents_affected: Optional[list[str]] = None,
    ) -> ExecutionMode:
        """Monitor connection and switch to simulated if connection lost."""
        if current_mode != ExecutionMode.LIVE:
            return current_mode

        # Check connection health periodically
        current_time = datetime.utcnow().timestamp()
        if current_time - self._last_health_check < self._health_check_interval:
            return current_mode

        self._last_health_check = current_time

        try:
            if not await self.check_connection_health():
                self._health_check_failures += 1

                if self._health_check_failures >= self._max_health_failures:
                    logger.warning(
                        "Live connection lost after %d failures. Switching to simulated mode.",
                        self._health_check_failures,
                    )

                    await self.set_mode(
                        ExecutionMode.SIMULATED,
                        reason=f"Live connection lost ({self._health_check_failures} failures)",
                        agents_affected=agents_affected,
                    )

                    self._health_check_failures = 0
                    return ExecutionMode.SIMULATED
            else:
                self._health_check_failures = 0
                self._connection_established = True

        except Exception as e:
            logger.error("Connection monitoring error: %s", e)
            self._health_check_failures += 1

        return current_mode

    async def handle_connection_loss(
        self,
        current_mode: ExecutionMode,
        agents_affected: Optional[list[str]] = None,
    ) -> ExecutionMode:
        """Handle connection loss and switch to simulated mode."""
        if current_mode != ExecutionMode.LIVE:
            return current_mode

        logger.warning("Live connection lost. Switching to simulated mode.")

        await self.set_mode(
            ExecutionMode.SIMULATED,
            reason="Live connection lost",
            agents_affected=agents_affected,
        )

        return ExecutionMode.SIMULATED

    def get_current_mode(self) -> ExecutionMode:
        """Get current execution mode."""
        return self._current_mode

    def is_live_mode(self) -> bool:
        """Check if currently in live mode."""
        return self._current_mode == ExecutionMode.LIVE

    def is_simulated_mode(self) -> bool:
        """Check if currently in simulated mode."""
        return self._current_mode == ExecutionMode.SIMULATED

    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status information."""
        return {
            "current_mode": self._current_mode.value,
            "connection_established": self._connection_established,
            "health_check_failures": self._health_check_failures,
            "last_health_check": self._last_health_check,
        }

    def reset_connection_status(self) -> None:
        """Reset connection status after reconnection."""
        self._connection_established = True
        self._health_check_failures = 0
        self._last_health_check = 0.0

    async def simulate_connection_loss(self) -> None:
        """Simulate connection loss for testing."""
        logger.warning("Simulating connection loss for testing purposes.")
        await self.set_mode(
            ExecutionMode.SIMULATED,
            reason="Connection loss simulated for testing",
        )
