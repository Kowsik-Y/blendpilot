"""
BlendPilot — Metrics Dashboard Backend

Performance monitoring and metrics collection with:
- Timing breakdown per agent at pipeline completion
- CPU and memory usage tracking
- QA pass rates for complex scenes
- Historical performance analysis
- CSV/JSON export support
"""

from __future__ import annotations

import csv
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("blendpilot.core.metrics")


@dataclass
class AgentTiming:
    """Timing data for an agent execution."""
    agent_name: str
    start_time: float
    end_time: float
    duration_seconds: float
    status: str
    repair_count: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class ResourceUsage:
    """Resource usage metrics."""
    cpu_percent: float = 0.0
    memory_gb: float = 0.0
    gpu_percent: float = 0.0
    threads: int = 0


@dataclass
class QualityMetrics:
    """Quality assurance metrics."""
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    pass_rate: float = 0.0


class MetricsCollector:
    """
    Collects and reports performance metrics for BlendPilot workflows.

    Features:
    - Timing breakdown per agent
    - CPU and memory usage tracking
    - QA pass rates
    - Historical analysis
    - Export to CSV/JSON
    """

    def __init__(
        self,
        output_dir: str = "/tmp/blendpilot/metrics",
        retention_days: int = 30,
    ):
        self.output_dir = Path(output_dir)
        self.retention_days = retention_days

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Current session metrics
        self._session_metrics: List[Dict[str, Any]] = []
        self._agent_timings: Dict[str, List[float]] = {}
        self._resource_samples: List[Dict[str, Any]] = []

        # Historical metrics
        self._historical_metrics: List[Dict[str, Any]] = []

    def start_session(self, session_id: str, user_id: Optional[str] = None) -> None:
        """Start metrics collection for a new session."""
        self._session_metrics = [{
            "session_id": session_id,
            "user_id": user_id,
            "started_at": datetime.utcnow().isoformat(),
            "agents": {},
            "resources": [],
            "errors": [],
        }]

    def record_agent_timing(
        self,
        session_id: str,
        agent_name: str,
        duration_seconds: float,
        status: str = "completed",
        repair_count: int = 0,
        errors: Optional[List[str]] = None,
    ) -> None:
        """Record timing for an agent execution."""
        if not self._session_metrics:
            return

        agent_data = {
            "agent": agent_name,
            "duration_seconds": duration_seconds,
            "status": status,
            "repair_count": repair_count,
            "errors": errors or [],
        }

        self._session_metrics[-1]["agents"][agent_name] = agent_data

        # Track historical timing
        if agent_name not in self._agent_timings:
            self._agent_timings[agent_name] = []
        self._agent_timings[agent_name].append(duration_seconds)

    def record_resource_usage(
        self,
        cpu_percent: float,
        memory_gb: float,
        gpu_percent: Optional[float] = None,
    ) -> None:
        """Record resource usage sample."""
        sample = {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu_percent": cpu_percent,
            "memory_gb": memory_gb,
            "gpu_percent": gpu_percent or 0.0,
        }

        if self._session_metrics:
            self._session_metrics[-1]["resources"].append(sample)

        self._resource_samples.append(sample)

    def record_qa_result(
        self,
        session_id: str,
        checks_passed: int,
        checks_total: int,
    ) -> None:
        """Record QA result for a session."""
        if not self._session_metrics:
            return

        self._session_metrics[-1]["qa"] = {
            "checks_passed": checks_passed,
            "checks_total": checks_total,
            "pass_rate": checks_passed / checks_total if checks_total > 0 else 0.0,
        }

    def record_error(
        self,
        session_id: str,
        error_type: str,
        error_message: str,
        agent: Optional[str] = None,
    ) -> None:
        """Record an error for a session."""
        if not self._session_metrics:
            return

        error = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "agent": agent,
        }

        self._session_metrics[-1]["errors"].append(error)

    def end_session(
        self,
        session_id: str,
        completed_agents: int,
        failed_agents: int,
        total_agents: int,
    ) -> Dict[str, Any]:
        """End metrics collection for a session and return summary."""
        if not self._session_metrics:
            return {}

        session = self._session_metrics[-1]
        session["completed_agents"] = completed_agents
        session["failed_agents"] = failed_agents
        session["total_agents"] = total_agents
        session["finished_at"] = datetime.utcnow().isoformat()
        session["duration_seconds"] = (
            datetime.fromisoformat(session["finished_at"])
            - datetime.fromisoformat(session["started_at"])
        ).total_seconds()

        # Save to file
        self._save_session(session)

        # Store in historical metrics
        self._historical_metrics.append(session)

        return self._generate_summary(session)

    def _save_session(self, session: Dict[str, Any]) -> Path:
        """Save session metrics to file."""
        session_id = session["session_id"]
        filename = f"session_{session_id}.json"
        filepath = self.output_dir / filename

        with open(filepath, "w") as f:
            json.dump(session, f, indent=2)

        logger.info("Saved session metrics to %s", filepath)
        return filepath

    def _generate_summary(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of session metrics."""
        agents = session.get("agents", {})

        timing_breakdown = {}
        for agent_name, agent_data in agents.items():
            timing_breakdown[agent_name] = {
                "duration_seconds": agent_data.get("duration_seconds", 0),
                "status": agent_data.get("status", "unknown"),
            }

        total_duration = session.get("duration_seconds", 0)
        avg_agent_duration = (
            sum(a.get("duration_seconds", 0)
                for a in agents.values()) / len(agents)
            if agents else 0
        )

        return {
            "session_id": session["session_id"],
            "total_duration_seconds": total_duration,
            "avg_agent_duration_seconds": avg_agent_duration,
            "timing_breakdown": timing_breakdown,
            "completed_agents": session.get("completed_agents", 0),
            "failed_agents": session.get("failed_agents", 0),
            "total_agents": session.get("total_agents", 0),
            "error_count": len(session.get("errors", [])),
        }

    def get_agent_timing_breakdown(self) -> Dict[str, Dict[str, float]]:
        """Get timing breakdown across all sessions."""
        breakdown = {}

        for agent_name, timings in self._agent_timings.items():
            if timings:
                breakdown[agent_name] = {
                    "count": len(timings),
                    "min_seconds": min(timings),
                    "max_seconds": max(timings),
                    "avg_seconds": sum(timings) / len(timings),
                    "total_seconds": sum(timings),
                }

        return breakdown

    def get_resource_usage_summary(self) -> Dict[str, float]:
        """Get resource usage summary."""
        if not self._resource_samples:
            return {}

        cpus = [s["cpu_percent"] for s in self._resource_samples]
        memories = [s["memory_gb"] for s in self._resource_samples]

        return {
            "cpu_percent": {
                "min": min(cpus),
                "max": max(cpus),
                "avg": sum(cpus) / len(cpus),
            },
            "memory_gb": {
                "min": min(memories),
                "max": max(memories),
                "avg": sum(memories) / len(memories),
            },
        }

    def export_to_csv(self, filename: Optional[str] = None) -> Path:
        """Export metrics to CSV."""
        filename = filename or f"metrics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.output_dir / filename

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "session_id",
                "agent",
                "duration_seconds",
                "status",
                "repair_count",
                "errors",
                "cpu_percent",
                "memory_gb",
                "timestamp",
            ])

            # Data rows
            for session in self._historical_metrics:
                session_id = session.get("session_id", "unknown")
                agents = session.get("agents", {})
                resources = session.get("resources", [])

                for agent_name, agent_data in agents.items():
                    resource = resources[0] if resources else {}
                    writer.writerow([
                        session_id,
                        agent_name,
                        agent_data.get("duration_seconds", ""),
                        agent_data.get("status", ""),
                        agent_data.get("repair_count", ""),
                        "; ".join(agent_data.get("errors", [])),
                        resource.get("cpu_percent", ""),
                        resource.get("memory_gb", ""),
                        session.get("started_at", ""),
                    ])

        logger.info("Exported metrics to %s", filepath)
        return filepath

    def export_to_json(self, filename: Optional[str] = None) -> Path:
        """Export metrics to JSON."""
        filename = filename or f"metrics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename

        with open(filepath, "w") as f:
            json.dump({
                "metadata": {
                    "exported_at": datetime.utcnow().isoformat(),
                    "session_count": len(self._historical_metrics),
                },
                "historical_metrics": self._historical_metrics,
                "agent_timings": self._agent_timings,
            }, f, indent=2)

        logger.info("Exported metrics to %s", filepath)
        return filepath

    def clear_history(self) -> None:
        """Clear all historical metrics."""
        self._historical_metrics.clear()
        self._agent_timings.clear()
        self._resource_samples.clear()

    def cleanup_old_metrics(self) -> int:
        """Remove metrics older than retention period."""
        deleted = 0
        cutoff = datetime.utcnow().timestamp() - (self.retention_days * 86400)

        for filepath in self.output_dir.glob("session_*.json"):
            try:
                if filepath.stat().st_mtime < cutoff:
                    filepath.unlink()
                    deleted += 1
            except Exception as e:
                logger.warning("Failed to delete %s: %s", filepath, e)

        logger.info("Deleted %d old metrics files", deleted)
        return deleted
