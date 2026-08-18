"""
BlendPilot — Self-Repair Manager

Implements automated error recovery with:
- 5 repair strategies (simplify geometry, simplify materials, reduce lighting, scale down scene, skip non-critical features)
- Max 5 repair attempts per agent
- Repair count and reason streaming to clients
- Error if repair attempts exceed 5
- Original error context preservation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from services.streaming import StreamingOrchestrator

logger = logging.getLogger("blendpilot.core.self_repair")


class RepairStrategy(Enum):
    """Available repair strategies."""
    SIMPLIFY_GEOMETRY = "simplify_geometry"
    SIMPLIFY_MATERIALS = "simplify_materials"
    REDUCE_LIGHTING = "reduce_lighting"
    SCALE_DOWN_SCENE = "scale_down_scene"
    SKIP_NON_CRITICAL = "skip_non_critical"


class MaxRepairAttemptsExceeded(Exception):
    """Raised when max repair attempts are exceeded."""
    pass


@dataclass
class RepairResult:
    """Result of a repair attempt."""
    success: bool
    strategy_used: Optional[RepairStrategy]
    reason: str
    original_error: str
    repair_count: int


@dataclass
class AgentError:
    """Error from agent execution."""
    agent_name: str
    error_message: str
    error_type: str
    context: Dict[str, Any]
    timestamp: str


class SelfRepairManager:
    """
    Manages automated self-repair for agent execution failures.

    Features:
    - 5 repair strategies in priority order
    - Max 5 repair attempts per agent
    - Repair count and reason streaming
    - Original error context preservation
    """

    MAX_REPAIR_ATTEMPTS = 5

    STRATEGIES = [
        RepairStrategy.SIMPLIFY_GEOMETRY,
        RepairStrategy.SIMPLIFY_MATERIALS,
        RepairStrategy.REDUCE_LIGHTING,
        RepairStrategy.SCALE_DOWN_SCENE,
        RepairStrategy.SKIP_NON_CRITICAL,
    ]

    def __init__(
        self,
        streaming: Optional[StreamingOrchestrator] = None,
        max_attempts: int = MAX_REPAIR_ATTEMPTS,
    ):
        self.streaming = streaming
        self.max_attempts = max_attempts
        self._repair_attempts: Dict[str, int] = {}

    async def _emit_repair_update(
        self,
        agent_name: str,
        repair_count: int,
        strategy: RepairStrategy,
        reason: str,
    ) -> None:
        """Emit repair status update to streaming."""
        if self.streaming:
            try:
                await self.streaming.broadcast_agent_update(
                    agent_name=agent_name,
                    status="repairing",
                    repair_count=repair_count,
                    reason=f"{strategy.value}: {reason}",
                )
            except Exception as e:
                logger.warning("Failed to emit repair update: %s", e)

    async def _apply_repair_strategy(
        self,
        strategy: RepairStrategy,
        error: AgentError,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply a repair strategy and return modified execution context."""
        # Strategy implementations
        if strategy == RepairStrategy.SIMPLIFY_GEOMETRY:
            return self._simplify_geometry(error, context)
        elif strategy == RepairStrategy.SIMPLIFY_MATERIALS:
            return self._simplify_materials(error, context)
        elif strategy == RepairStrategy.REDUCE_LIGHTING:
            return self._reduce_lighting(error, context)
        elif strategy == RepairStrategy.SCALE_DOWN_SCENE:
            return self._scale_down_scene(error, context)
        elif strategy == RepairStrategy.SKIP_NON_CRITICAL:
            return self._skip_non_critical(error, context)
        else:
            return context

    def _simplify_geometry(
        self,
        error: AgentError,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Simplify geometry in context."""
        context["geometry_complexity"] = context.get(
            "geometry_complexity", "high")
        if context["geometry_complexity"] == "high":
            context["geometry_complexity"] = "medium"
        elif context["geometry_complexity"] == "medium":
            context["geometry_complexity"] = "low"
        context["decimation_applied"] = True
        return context

    def _simplify_materials(
        self,
        error: AgentError,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Simplify materials in context."""
        context["material_complexity"] = context.get(
            "material_complexity", "high")
        if context["material_complexity"] == "high":
            context["material_complexity"] = "medium"
        elif context["material_complexity"] == "medium":
            context["material_complexity"] = "low"
        context["use_principled_bsdf"] = True
        return context

    def _reduce_lighting(
        self,
        error: AgentError,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Reduce lighting complexity in context."""
        context["lighting_complexity"] = context.get(
            "lighting_complexity", "high")
        if context["lighting_complexity"] == "high":
            context["lighting_complexity"] = "medium"
        elif context["lighting_complexity"] == "medium":
            context["lighting_complexity"] = "low"
        context["lighting_count"] = 2  # Reduce to 2 lights
        return context

    def _scale_down_scene(
        self,
        error: AgentError,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Scale down scene in context."""
        context["scene_scale_factor"] = context.get("scene_scale_factor", 1.0)
        context["scene_scale_factor"] *= 0.5  # Scale by 50%
        return context

    def _skip_non_critical(
        self,
        error: AgentError,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Skip non-critical features in context."""
        context["non_critical_features"] = context.get(
            "non_critical_features", [])
        if context["non_critical_features"]:
            # Remove one non-critical feature
            context["non_critical_features"].pop()
        return context

    async def attempt_repair(
        self,
        agent_name: str,
        error: AgentError,
        execution_context: Dict[str, Any],
        execute_fn: Callable[[Dict[str, Any]], Any],
    ) -> RepairResult:
        """Attempt to repair an agent execution error."""
        current_attempts = self._repair_attempts.get(agent_name, 0) + 1
        self._repair_attempts[agent_name] = current_attempts

        logger.info(
            "Repair attempt %d/%d for agent %s: %s",
            current_attempts,
            self.max_attempts,
            agent_name,
            error.error_message,
        )

        # Stream repair status
        await self._emit_repair_update(
            agent_name=agent_name,
            repair_count=current_attempts,
            strategy=self.STRATEGIES[current_attempts - 1],
            reason=error.error_message,
        )

        if current_attempts > self.max_attempts:
            raise MaxRepairAttemptsExceeded(
                f"Agent {agent_name} exceeded max repair attempts ({self.max_attempts})"
            )

        # Try each strategy in order until one works
        for strategy in self.STRATEGIES[current_attempts - 1:]:
            try:
                modified_context = await self._apply_repair_strategy(
                    strategy, error, execution_context.copy()
                )
                result = await execute_fn(modified_context)

                if result.get("success", False):
                    return RepairResult(
                        success=True,
                        strategy_used=strategy,
                        reason=f"Repaired via {strategy.value}",
                        original_error=error.error_message,
                        repair_count=current_attempts,
                    )
            except Exception as e:
                logger.warning(
                    "Repair strategy %s failed: %s",
                    strategy.value, e
                )
                continue

        # All strategies failed
        return RepairResult(
            success=False,
            strategy_used=None,
            reason="All repair strategies exhausted",
            original_error=error.error_message,
            repair_count=current_attempts,
        )

    async def execute_with_repair(
        self,
        agent_name: str,
        execute_fn: Callable[[Dict[str, Any]], Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute agent with automatic repair on failure."""
        try:
            result = await execute_fn(context)
            return result
        except Exception as e:
            error = AgentError(
                agent_name=agent_name,
                error_message=str(e),
                error_type=type(e).__name__,
                context=context.copy(),
                timestamp=str(datetime.utcnow()),
            )

            # Reset repair count for new error
            self._repair_attempts[agent_name] = 0

            repair_result = await self.attempt_repair(
                agent_name=agent_name,
                error=error,
                execution_context=context.copy(),
                execute_fn=execute_fn,
            )

            if repair_result.success:
                # Try execution again with modified context
                try:
                    return await execute_fn(repair_result.context)
                except Exception as e:
                    error = AgentError(
                        agent_name=agent_name,
                        error_message=str(e),
                        error_type=type(e).__name__,
                        context=context.copy(),
                        timestamp=str(datetime.utcnow()),
                    )
                    # Second attempt with same repair
                    repair_result = await self.attempt_repair(
                        agent_name=agent_name,
                        error=error,
                        execution_context=context.copy(),
                        execute_fn=execute_fn,
                    )
                    if repair_result.success:
                        return await execute_fn(repair_result.context)
                    raise MaxRepairAttemptsExceeded(
                        f"Agent {agent_name} repair failed: {repair_result.reason}"
                    )

            raise MaxRepairAttemptsExceeded(
                f"Agent {agent_name} repair failed: {repair_result.reason}"
            )

    def get_repair_count(self, agent_name: str) -> int:
        """Get current repair count for an agent."""
        return self._repair_attempts.get(agent_name, 0)

    def reset_repair_count(self, agent_name: str) -> None:
        """Reset repair count for an agent."""
        if agent_name in self._repair_attempts:
            del self._repair_attempts[agent_name]

    def reset_all(self) -> None:
        """Reset all repair counts."""
        self._repair_attempts.clear()
