"""
BlendPilot AI — Autonomous Modeling Agent

Workflow 5: Executes 3D modeling operations sequentially, calls Blender MCP tools,
tracks created objects, and manages rollback checkpoints.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp_servers.blender.server import BlenderMCPServer
from schemas.plan import DesignPlan, StepStatus

logger = logging.getLogger("blendpilot.agents.modeling")


class ModelingAgent:
    """Agent that executes step-by-step 3D modeling operations in Blender."""

    def __init__(self, mcp_server: BlenderMCPServer | None = None):
        self.mcp_server = mcp_server or BlenderMCPServer()

    async def execute(self, plan: DesignPlan) -> dict[str, Any]:
        """Execute all modeling steps in the DesignPlan."""
        logger.info("Executing 3D modeling operations for plan: %s", plan.spec_id)

        created_objects: list[str] = []
        execution_logs: list[dict[str, Any]] = []

        for i, step in enumerate(plan.steps):
            logger.info("Executing Step %d/%d: %s", step.step_id, len(plan.steps), step.description)
            step.status = StepStatus.IN_PROGRESS
            plan.current_step_index = i

            res = await self.mcp_server.call_tool(step.tool, step.parameters)
            success = res.get("success", False)

            if success:
                step.status = StepStatus.COMPLETED
                # Track newly created objects
                if step.tool == "create_primitive" and "object_name" in res:
                    created_objects.append(res["object_name"])
                elif step.tool == "duplicate_object" and "new_object" in res and res["new_object"]:
                    created_objects.append(res["new_object"])
                elif "name" in step.parameters and step.parameters["name"] not in created_objects:
                    created_objects.append(step.parameters["name"])
            else:
                step.status = StepStatus.FAILED
                step.error_message = res.get("error", "Unknown error during tool execution")
                logger.error("Step %d failed: %s", step.step_id, step.error_message)

            execution_logs.append({
                "step_id": step.step_id,
                "tool": step.tool,
                "success": success,
                "response": res,
            })

        all_completed = all(s.status == StepStatus.COMPLETED for s in plan.steps)
        plan.status = StepStatus.COMPLETED if all_completed else StepStatus.FAILED

        return {
            "success": all_completed,
            "created_objects": created_objects,
            "plan": plan,
            "logs": execution_logs,
        }
