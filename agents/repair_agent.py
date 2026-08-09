"""
BlendPilot AI — Unified Repair Agent

Stage 13: Targeted Repair Agent
Produces a structured RepairPlan and executes targeted repairs.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from mcp_servers.blender.server import BlenderMCPServer
from schemas.design import DesignSpec
from schemas.plan_state import RepairPlan, RepairStep
from services.llm import LLMService

logger = logging.getLogger("blendpilot.agents.repair")

_REPAIR_SYSTEM_PROMPT = """
You are the targeted Repair Agent for a 3D asset generation pipeline.

You receive:
- The original Design Intent
- Geometry Validation Report
- Vision Critique Report
- Scene State (current objects and materials)

Your task: analyze the feedback and generate a JSON RepairPlan to fix the issues.
You must modify ONLY the affected objects whenever possible. DO NOT regenerate the entire scene.

Available corrective operations (MCP tools):
- edit_mesh
- add_modifier
- apply_modifier
- create_material
- assign_material
- setup_studio_lighting
- render_preview
- delete_object
- create_primitive
- set_transform

For each repair step, you must provide:
- affected_object: Name of the object being repaired
- problem: Description of the issue being fixed
- corrective_operation: Name of the operation to execute
- parameters: Execution parameters for the operation
- reason: Explanation of why this operation fixes the problem

Respond ONLY with a JSON object matching this schema:
{
  "steps": [
    {
      "affected_object": "str",
      "problem": "str",
      "corrective_operation": "str",
      "parameters": {},
      "reason": "str"
    }
  ]
}
"""


class RepairAgent:
    """Targeted repair agent that plans and executes fixes via MCP calls."""

    def __init__(
        self,
        mcp_server: BlenderMCPServer | None = None,
        llm_service: LLMService | None = None,
        mock_mode: bool = False,
    ):
        self.mcp_server = mcp_server or BlenderMCPServer()
        self.llm_service = llm_service
        self.mock_mode = mock_mode

    async def execute(
        self,
        intent: dict[str, Any],
        validation_report: dict[str, Any],
        vision_report: dict[str, Any],
        scene_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Produce and execute a targeted RepairPlan.

        Args:
            intent: Original user intent (DesignSpec dict).
            validation_report: Geometry QA results.
            vision_report: Vision Critique results.
            scene_state: Current state of the Blender scene.

        Returns:
            dict containing:
                - repair_plan: The generated RepairPlan dict
                - ops_executed: int
                - success: bool
        """
        logger.info("RepairAgent planning targeted repairs...")

        # 1. Produce Repair Plan
        if self.mock_mode or not self.llm_service or not self.llm_service.config.api_key:
            plan = self._heuristic_repairs(validation_report, vision_report)
        else:
            try:
                plan = await self._llm_generate_repairs(
                    intent=intent,
                    validation_report=validation_report,
                    vision_report=vision_report,
                    scene_state=scene_state,
                )
            except Exception as exc:
                logger.warning("LLM repair planning failed (%s), using heuristic", exc)
                plan = self._heuristic_repairs(validation_report, vision_report)

        # 2. Execute Repair Plan
        logger.info("Executing %d targeted repair steps.", len(plan.steps))
        ops_executed = 0
        success = True

        if not self.mock_mode:
            for step in plan.steps:
                logger.info("  Repair step: %s on %s (Reason: %s)", step.corrective_operation, step.affected_object, step.reason)
                try:
                    result = await self.mcp_server.call_tool(step.corrective_operation, step.parameters)
                    if result.get("success", False):
                        ops_executed += 1
                    else:
                        logger.error("  Repair step failed: %s", result)
                        success = False
                except Exception as e:
                    logger.error("  Repair step raised exception: %s", e)
                    success = False

        return {
            "success": success,
            "ops_executed": ops_executed,
            "repair_plan": plan.model_dump(),
        }

    async def _llm_generate_repairs(
        self,
        intent: dict[str, Any],
        validation_report: dict[str, Any],
        vision_report: dict[str, Any],
        scene_state: dict[str, Any],
    ) -> RepairPlan:
        """Ask the LLM to generate a targeted RepairPlan."""
        user_msg = (
            f"Original Intent: {json.dumps(intent)}\n"
            f"Scene State: {json.dumps(scene_state)}\n"
            f"Geometry Validation: {json.dumps(validation_report)}\n"
            f"Vision Critique: {json.dumps(vision_report)}\n\n"
            "Generate a targeted RepairPlan."
        )

        response = await self.llm_service.generate(
            prompt=user_msg,
            system_prompt=_REPAIR_SYSTEM_PROMPT.strip(),
            response_format={"type": "json_object"},
        )

        if not response:
            raise ValueError("Empty LLM response")

        clean = re.sub(r"^```json\s*|\s*```$", "", response.strip(), flags=re.MULTILINE)
        parsed = json.loads(clean)

        return RepairPlan.model_validate(parsed)

    def _heuristic_repairs(
        self,
        validation_report: dict[str, Any],
        vision_report: dict[str, Any],
    ) -> RepairPlan:
        """Rule-based fallback repair plan."""
        steps = []
        
        # Check geometry errors
        for check in validation_report.get("checks", []):
            if check.get("passed") is False:
                obj = check.get("object", "Unknown")
                prob = check.get("message", "Unknown geometry issue")
                if check.get("check_name") == "duplicate_vertices":
                    steps.append(RepairStep(
                        affected_object=obj,
                        problem=prob,
                        corrective_operation="edit_mesh",
                        parameters={"object_name": obj, "operation": "merge_doubles"},
                        reason="Merge by distance removes duplicate vertices"
                    ))
                elif check.get("check_name") == "missing_required_object":
                    steps.append(RepairStep(
                        affected_object=obj,
                        problem=prob,
                        corrective_operation="create_primitive",
                        parameters={"type": "cube", "name": obj},
                        reason="Recreate missing required object"
                    ))

        # Check visual errors
        if vision_report.get("overall_result") == "FAIL":
            for err in vision_report.get("obvious_visual_errors", []):
                steps.append(RepairStep(
                    affected_object="Scene",
                    problem=err,
                    corrective_operation="setup_studio_lighting",
                    parameters={"key_energy": 1600.0, "fill_energy": 600.0, "rim_energy": 1000.0},
                    reason="Boost lighting to fix visual clarity issues"
                ))
            
            # Always re-render if visual changes made
            steps.append(RepairStep(
                affected_object="Scene",
                problem="Preview outdated",
                corrective_operation="render_preview",
                parameters={"output_path": "output/repair_preview.png"},
                reason="Generate updated preview for validation"
            ))

        # Default fallback if empty
        if not steps:
            steps.append(RepairStep(
                affected_object="Scene",
                problem="Unknown error",
                corrective_operation="setup_studio_lighting",
                parameters={"key_energy": 1000.0},
                reason="Fallback repair operation"
            ))

        return RepairPlan(steps=steps)
