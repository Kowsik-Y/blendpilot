"""
BlendPilot — Time Budget Manager

Enforces per-agent time budgets with:
- Modeling: 120s budget, 20% warning threshold
- Other phases: 60s budget
- Logging warnings at 120% of budget
- Automatic continuation after warning
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("blendpilot.core.time_budget")


class TimeBudgetExceeded(Exception):
    """Raised when time budget is exceeded (but execution continues with warning)."""
    pass


@dataclass
class TimeBudget:
    """Time budget configuration for an operation."""
    name: str
    budget_seconds: float
    warning_threshold: float = 1.2  # 20% over budget

    @property
    def max_seconds(self) -> float:
        """Maximum seconds before warning."""
        return self.budget_seconds * self.warning_threshold


@dataclass
class ExecutionResult:
    """Result of timed execution."""
    success: bool
    elapsed_seconds: float
    warning: Optional[str] = None
    output: Optional[Any] = None


class TimeBudgetManager:
    """
    Manages time budgets for operations with warning thresholds.

    Features:
    - Configurable time budgets per operation type
    - Warning at 120% of budget (no interruption)
    - Detailed timing reports
    - Per-operation budget tracking
    """

    DEFAULT_BUDGETS = {
        "modeling": 120.0,
        "rendering": 60.0,
        "material": 60.0,
        "export": 60.0,
        "qa": 60.0,
        "default": 60.0,
    }

    def __init__(
        self,
        budgets: Optional[Dict[str, float]] = None,
    ):
        self.budgets = {**self.DEFAULT_BUDGETS, **(budgets or {})}

        # Track timing per operation
        self._timings: Dict[str, list[float]] = {}
        self._current_operations: Dict[str, float] = {}

    def get_budget(self, operation_name: str) -> TimeBudget:
        """Get time budget for an operation."""
        budget_seconds = self.budgets.get(
            operation_name, self.budgets["default"])
        return TimeBudget(
            name=operation_name,
            budget_seconds=budget_seconds,
        )

    def start_operation(self, operation_name: str) -> float:
        """Start timing an operation and return start time."""
        start_time = time.monotonic()
        self._current_operations[operation_name] = start_time
        return start_time

    def end_operation(
        self,
        operation_name: str,
        start_time: float,
        success: bool = True,
        output: Optional[Any] = None,
    ) -> ExecutionResult:
        """End timing an operation and return result."""
        elapsed = time.monotonic() - start_time

        # Track timing history
        if operation_name not in self._timings:
            self._timings[operation_name] = []
        self._timings[operation_name].append(elapsed)

        # Check budget
        budget = self.get_budget(operation_name)
        warning = None

        if elapsed > budget.max_seconds:
            warning = (
                f"Operation '{operation_name}' exceeded time budget: "
                f"{elapsed:.2f}s > {budget.max_seconds:.2f}s "
                f"(budget: {budget.budget_seconds:.2f}s)"
            )
            logger.warning(warning)

        # Remove from current operations
        if operation_name in self._current_operations:
            del self._current_operations[operation_name]

        return ExecutionResult(
            success=success,
            elapsed_seconds=elapsed,
            warning=warning,
            output=output,
        )

    async def execute_with_budget(
        self,
        operation_name: str,
        operation_fn: Callable[[], Any],
        *args,
        **kwargs,
    ) -> ExecutionResult:
        """Execute an operation with time budget monitoring."""
        start_time = self.start_operation(operation_name)

        try:
            result = await operation_fn(*args, **kwargs) if callable(operation_fn) else operation_fn
            return self.end_operation(operation_name, start_time, True, result)
        except Exception as e:
            return self.end_operation(operation_name, start_time, False, None)

    def get_timing_report(self) -> Dict[str, Dict[str, float]]:
        """Get timing breakdown per operation type."""
        report = {}
        for operation, timings in self._timings.items():
            if timings:
                report[operation] = {
                    "count": len(timings),
                    "min_seconds": min(timings),
                    "max_seconds": max(timings),
                    "avg_seconds": sum(timings) / len(timings),
                    "total_seconds": sum(timings),
                }
        return report

    def get_operation_timing(self, operation_name: str) -> Optional[Dict[str, float]]:
        """Get timing statistics for a specific operation."""
        if operation_name not in self._timings:
            return None

        timings = self._timings[operation_name]
        return {
            "count": len(timings),
            "min_seconds": min(timings),
            "max_seconds": max(timings),
            "avg_seconds": sum(timings) / len(timings),
        }

    def is_operation_running(self, operation_name: str) -> bool:
        """Check if an operation is currently running."""
        return operation_name in self._current_operations

    def get_remaining_time(self, operation_name: str) -> float:
        """Get remaining time for a running operation."""
        if operation_name not in self._current_operations:
            return 0.0

        start_time = self._current_operations[operation_name]
        elapsed = time.monotonic() - start_time
        budget = self.get_budget(operation_name)

        return max(0.0, budget.max_seconds - elapsed)

    def clear_history(self) -> None:
        """Clear timing history."""
        self._timings.clear()
        self._current_operations.clear()


class AgentTimeBudgetManager(TimeBudgetManager):
    """Time budget manager specifically for agent operations."""

    AGENT_BUDGETS = {
        "intent": 60.0,
        "scene": 60.0,
        "research": 120.0,
        "planning": 60.0,
        "modeling": 120.0,
        "material": 60.0,
        "geometry_qa": 60.0,
        "visual_critic": 60.0,
        "feedback": 60.0,
        "export": 60.0,
    }

    def __init__(self):
        super().__init__(budgets=self.AGENT_BUDGETS)
