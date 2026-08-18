"""
BlendPilot — Autonomous Modeling Agent

Workflow 5: Executes 3D modeling operations sequentially, calls Blender MCP tools,
tracks created objects, and uses LLM for adaptive error recovery when steps fail.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from mcp_servers.blender.server import BlenderMCPServer
from schemas.plan import DesignPlan, StepStatus
from services.llm import LLMService

logger = logging.getLogger("blendpilot.agents.modeling")


class ModelingAgent:
    """Agent that executes step-by-step 3D modeling operations in Blender.

    When a step fails, uses LLM to reason about alternative approaches
    and generate recovery operations.
    """

    def __init__(
        self,
        mcp_server: BlenderMCPServer | None = None,
        llm_service: LLMService | None = None,
        event_callback: Callable[[dict[str, Any]],
                                 Awaitable[None]] | None = None,
    ):
        self.mcp_server = mcp_server or BlenderMCPServer()
        self.llm_service = llm_service
        self.event_callback = event_callback

    async def _emit(self, payload: dict[str, Any]) -> None:
        """Emit live execution events without making modeling depend on transport."""
        if self.event_callback is None:
            return
        try:
            await self.event_callback(payload)
        except Exception as e:
            logger.warning("Modeling event callback failed: %s", e)

    async def execute(self, plan: DesignPlan) -> dict[str, Any]:
        """Execute all modeling steps in the DesignPlan with adaptive error recovery."""
        logger.info(
            "Executing 3D modeling operations for plan: %s", plan.spec_id)

        created_objects: list[str] = []
        execution_logs: list[dict[str, Any]] = []

        for i, step in enumerate(plan.steps):
            logger.info("Executing Step %d/%d: %s", step.step_id,
                        len(plan.steps), step.description)
            step.status = StepStatus.IN_PROGRESS
            plan.current_step_index = i

            await self._emit({
                "event": "tool_start",
                "agent_name": "modeling_agent",
                "step_id": step.step_id,
                "step_index": i,
                "total_steps": len(plan.steps),
                "description": step.description,
                "tool": step.tool,
                "parameters": step.parameters,
            })

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

                await self._emit({
                    "event": "tool_result",
                    "agent_name": "modeling_agent",
                    "step_id": step.step_id,
                    "status": "COMPLETED",
                    "tool": step.tool,
                    "description": step.description,
                    "parameters": step.parameters,
                    "response": res,
                    "created_objects": list(created_objects),
                })
            else:
                error_msg = res.get(
                    "error", "Unknown error during tool execution")
                logger.error("Step %d failed: %s", step.step_id, error_msg)

                await self._emit({
                    "event": "tool_result",
                    "agent_name": "modeling_agent",
                    "step_id": step.step_id,
                    "status": "FAILED",
                    "tool": step.tool,
                    "description": step.description,
                    "parameters": step.parameters,
                    "response": res,
                    "error": error_msg,
                })

                # Attempt LLM-powered error recovery
                recovered = await self._attempt_recovery(step, error_msg, created_objects)
                if recovered:
                    step.status = StepStatus.COMPLETED
                    if recovered.get("created_object"):
                        created_objects.append(recovered["created_object"])
                    logger.info(
                        "Step %d recovered via LLM adaptation", step.step_id)
                    await self._emit({
                        "event": "tool_recovered",
                        "agent_name": "modeling_agent",
                        "step_id": step.step_id,
                        "status": "COMPLETED",
                        "description": step.description,
                        "parameters": step.parameters,
                        "reasoning": recovered.get("reasoning", ""),
                        "created_objects": list(created_objects),
                    })
                else:
                    step.status = StepStatus.FAILED
                    step.error_message = error_msg

            execution_logs.append({
                "step_id": step.step_id,
                "tool": step.tool,
                "success": step.status == StepStatus.COMPLETED,
                "response": res,
            })

        all_completed = all(
            s.status == StepStatus.COMPLETED for s in plan.steps)
        plan.status = StepStatus.COMPLETED if all_completed else StepStatus.FAILED

        return {
            "success": all_completed,
            "created_objects": created_objects,
            "plan": plan,
            "logs": execution_logs,
        }

    async def _attempt_recovery(
        self,
        failed_step: Any,
        error_msg: str,
        created_objects: list[str],
    ) -> dict[str, Any] | None:
        """Use LLM to reason about and attempt alternative recovery for a failed step."""
        if not self.llm_service or not self.llm_service.config.api_key:
            return None

        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            import json

            system_prompt = (
                "You are a Blender 3D modeling expert. A modeling step has failed. "
                "Analyze the error and suggest a single corrected MCP tool call that achieves "
                "the same goal. Respond with a JSON object: "
                '{"tool": "<tool_name>", "parameters": {<params>}, "reasoning": "<why>"}'
            )
            user_prompt = (
                f"Failed step: {failed_step.description}\n"
                f"Tool: {failed_step.tool}\n"
                f"Parameters: {json.dumps(failed_step.parameters)}\n"
                f"Error: {error_msg}\n"
                f"Existing objects in scene: {created_objects}\n\n"
                f"Suggest a corrected tool call to achieve the same goal."
            )

            response = await self.llm_service.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                response_format={"type": "json_object"},
            )

            if not response:
                return None

            import re
            clean = re.sub(r"^```json\s*|\s*```$", "",
                           response.strip(), flags=re.MULTILINE)
            recovery = json.loads(clean)

            # Execute the recovery tool call
            tool_name = recovery.get("tool", failed_step.tool)
            params = recovery.get("parameters", failed_step.parameters)
            logger.info("LLM recovery: calling %s with %s (reason: %s)",
                        tool_name, params, recovery.get("reasoning", ""))

            retry_res = await self.mcp_server.call_tool(tool_name, params)
            if retry_res.get("success", False):
                result: dict[str, Any] = {
                    "success": True, "reasoning": recovery.get("reasoning", "")}
                if "object_name" in retry_res:
                    result["created_object"] = retry_res["object_name"]
                elif "name" in params:
                    result["created_object"] = params["name"]
                return result

        except Exception as e:
            logger.warning("LLM error recovery failed: %s", e)

        return None
