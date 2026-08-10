"""
BlendPilot AI — Agent Orchestration

Orchestrates the 10 specialized agents using LangGraph StateGraph:
1. IntentAgent      — Design Intent Understanding
2. SceneAgent       — Blender Scene Understanding
3. ResearchAgent    — Reference & Technical Research
4. PlanningAgent    — Step-by-Step Design Planning
5. ModelingAgent    — Autonomous Modeling & Checkpoints
6. MaterialAgent    — Materials, Lighting & Preview Rendering
7. GeometryQAAgent  — Deterministic Geometry QA & Repair Loops
8. VisualCriticAgent— Vision QA Critique & Self-Repair Loops
9. FeedbackAgent    — Human Review & Feedback Processing
10. ExportAgent     — Production Validation & Multi-Format Export
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from services.streaming import StreamingOrchestrator
from services.checkpoint import CheckpointManager
from services.resource_limiter import ResourceLimiter, ResourceLimitError

logger = logging.getLogger("blendpilot.core.orchestrator")


class AgentStatus(str, Enum):
    """Status of an agent execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REPAIRING = "repairing"


class WorkflowState(TypedDict):
    """Shared state for the workflow."""
    session_id: str
    user_prompt: str
    current_agent: str
    agent_history: List[Dict[str, Any]]
    blender_state: Optional[Dict[str, Any]]
    created_objects: List[str]
    mode: str  # "live" or "simulated"
    error_count: int
    repair_count: int


@dataclass
class AgentResult:
    """Result from an agent execution."""
    success: bool
    output: Dict[str, Any]
    errors: List[str]
    repair_attempts: int = 0


class AgentOrchestrator:
    """
    Orchestrates the 10-agent workflow using LangGraph StateGraph.

    Features:
    - Sequential agent execution with state passing
    - Per-agent time budget enforcement
    - Error handling with repair fallback
    - Streaming integration for real-time progress
    - Checkpoint support for long-running workflows
    """

    # Agent order and time budgets
    AGENT_ORDER = [
        "intent",
        "scene",
        "research",
        "planning",
        "modeling",
        "material",
        "geometry_qa",
        "visual_critic",
        "feedback",
        "export",
    ]

    TIME_BUDGETS = {
        "intent": 60,
        "scene": 60,
        "research": 120,
        "planning": 60,
        "modeling": 120,
        "material": 60,
        "geometry_qa": 60,
        "visual_critic": 60,
        "feedback": 60,
        "export": 60,
    }

    def __init__(
        self,
        mcp_server: Any,
        llm_service: Any,
        streaming: Optional[StreamingOrchestrator] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        resource_limiter: Optional[ResourceLimiter] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ):
        self.mcp_server = mcp_server
        self.llm_service = llm_service
        self.streaming = streaming
        self.checkpoint_manager = checkpoint_manager
        self.resource_limiter = resource_limiter
        self.event_callback = event_callback

        # Import agents
        from agents import (
            IntentAgent,
            SceneAgent,
            ResearchAgent,
            PlanningAgent,
            ModelingAgent,
            MaterialAgent,
            GeometryQAAgent,
            VisualCriticAgent,
            FeedbackAgent,
            ExportAgent,
        )

        self.agents = {
            "intent": IntentAgent(mcp_server, llm_service),
            "scene": SceneAgent(mcp_server, llm_service),
            "research": ResearchAgent(mcp_server, llm_service),
            "planning": PlanningAgent(mcp_server, llm_service),
            "modeling": ModelingAgent(mcp_server, llm_service),
            "material": MaterialAgent(mcp_server, llm_service),
            "geometry_qa": GeometryQAAgent(mcp_server, llm_service),
            "visual_critic": VisualCriticAgent(mcp_server, llm_service),
            "feedback": FeedbackAgent(mcp_service, llm_service),
            "export": ExportAgent(mcp_server, llm_service),
        }

        # Build state graph
        self.graph = self._build_graph()

        # Track execution time per agent
        self._agent_times: Dict[str, float] = {}

    async def _emit(self, payload: Dict[str, Any]) -> None:
        """Emit event to streaming and callback."""
        if self.event_callback:
            try:
                await self.event_callback(payload)
            except Exception as e:
                logger.warning("Event callback failed: %s", e)

        if self.streaming:
            try:
                await self.streaming.broadcast("agent_update", payload)
            except Exception as e:
                logger.warning("Streaming broadcast failed: %s", e)

    async def _log_agent_start(self, agent_name: str) -> float:
        """Log agent start time and emit event."""
        start_time = time.monotonic()
        await self._emit({
            "event": "agent_start",
            "agent": agent_name,
            "status": AgentStatus.RUNNING.value,
        })
        return start_time

    async def _log_agent_end(
        self,
        agent_name: str,
        start_time: float,
        success: bool,
        output: Dict[str, Any],
    ) -> None:
        """Log agent end time, emit event, and update timing."""
        elapsed = time.monotonic() - start_time
        self._agent_times[agent_name] = elapsed

        status = AgentStatus.COMPLETED if success else AgentStatus.FAILED
        await self._emit({
            "event": "agent_end",
            "agent": agent_name,
            "status": status.value,
            "elapsed_seconds": round(elapsed, 2),
            "output": output,
        })

    async def _enforce_time_budget(
        self,
        agent_name: str,
        start_time: float,
    ) -> None:
        """Enforce time budget and log warning if exceeded."""
        budget = self.TIME_BUDGETS.get(agent_name, 60)
        elapsed = time.monotonic() - start_time

        # Warn if exceeded 120% of budget
        if elapsed > budget * 1.2:
            logger.warning(
                "Agent %s exceeded time budget: %.2fs > %.2fs",
                agent_name, elapsed, budget * 1.2
            )
            await self._emit({
                "event": "time_budget_warning",
                "agent": agent_name,
                "elapsed_seconds": round(elapsed, 2),
                "budget_seconds": budget,
            })

    async def _check_resource_limits(self, user_id: str) -> None:
        """Check resource limits before running workflow."""
        if self.resource_limiter:
            await self.resource_limiter.check_resources(user_id)

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph for agent orchestration."""
        workflow = StateGraph(WorkflowState)

        # Add nodes for each agent
        for agent_name in self.AGENT_ORDER:
            workflow.add_node(agent_name, self._run_agent(agent_name))

        # Add entry point
        workflow.add_node("start", self._start_workflow)

        # Add exit point
        workflow.add_node("finish", self._finish_workflow)

        # Define edges
        workflow.add_edge("start", self.AGENT_ORDER[0])

        # Sequential execution
        for i, agent_name in enumerate(self.AGENT_ORDER[:-1]):
            next_agent = self.AGENT_ORDER[i + 1]
            workflow.add_edge(agent_name, next_agent)

        # Final agent leads to finish
        workflow.add_edge(self.AGENT_ORDER[-1], "finish")
        workflow.add_edge("finish", END)

        return workflow.compile()

    def _run_agent(self, agent_name: str):
        """Create a wrapper function to run an agent."""

        async def run_agent(state: WorkflowState) -> WorkflowState:
            agent = self.agents.get(agent_name)
            if not agent:
                state["error_count"] += 1
                state["agent_history"].append({
                    "agent": agent_name,
                    "status": AgentStatus.FAILED.value,
                    "error": f"Agent {agent_name} not found",
                })
                return state

            start_time = await self._log_agent_start(agent_name)

            try:
                # Run the agent with shared state
                result = await agent.execute(state)

                await self._enforce_time_budget(agent_name, start_time)
                await self._log_agent_end(agent_name, start_time, True, result)

                state["current_agent"] = agent_name
                state["agent_history"].append({
                    "agent": agent_name,
                    "status": AgentStatus.COMPLETED.value,
                    "output": result,
                })

                return state

            except Exception as e:
                logger.error("Agent %s failed: %s", agent_name, e)
                state["error_count"] += 1
                state["current_agent"] = agent_name
                state["agent_history"].append({
                    "agent": agent_name,
                    "status": AgentStatus.FAILED.value,
                    "error": str(e),
                })
                await self._log_agent_end(agent_name, start_time, False, {"error": str(e)})
                return state

        return run_agent

    async def _start_workflow(self, state: WorkflowState) -> WorkflowState:
        """Initialize workflow state."""
        state["agent_history"] = []
        state["created_objects"] = []
        state["error_count"] = 0
        state["repair_count"] = 0

        if self.checkpoint_manager:
            await self.checkpoint_manager.create_checkpoint(
                state["session_id"],
                state,
                None,
            )

        return state

    async def _finish_workflow(self, state: WorkflowState) -> WorkflowState:
        """Finalize workflow and save final checkpoint."""
        await self._emit({
            "event": "workflow_complete",
            "session_id": state["session_id"],
            "total_agents": len(self.AGENT_ORDER),
            "completed_agents": sum(
                1 for a in state["agent_history"]
                if a["status"] == AgentStatus.COMPLETED.value
            ),
            "failed_agents": sum(
                1 for a in state["agent_history"]
                if a["status"] == AgentStatus.FAILED.value
            ),
            "timing": self._agent_times,
        })

        if self.checkpoint_manager:
            await self.checkpoint_manager.create_checkpoint(
                state["session_id"],
                state,
                state.get("blender_state"),
            )

        return state

    async def execute(
        self,
        session_id: str,
        user_prompt: str,
        user_id: Optional[str] = None,
        mode: str = "live",
    ) -> WorkflowState:
        """Execute the full agent workflow."""
        # Check resource limits if user_id provided
        if user_id and self.resource_limiter:
            await self.resource_limiter.check_resources(user_id)

        # Initialize state
        state: WorkflowState = {
            "session_id": session_id,
            "user_prompt": user_prompt,
            "current_agent": "",
            "agent_history": [],
            "blender_state": None,
            "created_objects": [],
            "mode": mode,
            "error_count": 0,
            "repair_count": 0,
        }

        # Run the graph
        try:
            result = await self.graph.ainvoke(state)
            return result
        except Exception as e:
            logger.error("Workflow execution failed: %s", e)
            state["error_count"] += 1
            state["agent_history"].append({
                "agent": "orchestrator",
                "status": AgentStatus.FAILED.value,
                "error": str(e),
            })
            return state

    def get_timing_report(self) -> Dict[str, float]:
        """Get timing breakdown per agent."""
        return self._agent_times.copy()
