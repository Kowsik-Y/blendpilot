"""
BlendPilot AI — Refinement Agent

Stage 15: Human-in-the-loop Refinement
Produces a structured RepairPlan to modify an existing scene based on natural language feedback.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from mcp_servers.blender.server import BlenderMCPServer
from schemas.plan_state import RepairPlan, RepairStep
from services.llm import LLMService

logger = logging.getLogger("blendpilot.agents.refinement")

_REFINEMENT_SYSTEM_PROMPT = """
You are the Refinement Agent for a 3D asset generation pipeline.

You receive:
- The user's natural language modification request
- The current Scene State (objects and materials)

Your task: generate a JSON RepairPlan to apply the user's modifications.
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

For each modification step, you must provide:
- affected_object: Name of the object being modified
- problem: Description of the modification being applied
- corrective_operation: Name of the operation to execute
- parameters: Execution parameters for the operation
- reason: Explanation of why this operation achieves the user's goal

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

class RefinementAgent:
    """Agent that translates natural language feedback into targeted modifications."""

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
        user_prompt: str,
        scene_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Produce and execute a targeted Modification Plan based on user prompt.

        Args:
            user_prompt: User's modification request (e.g., "Make the legs thicker").
            scene_state: Current state of the Blender scene.

        Returns:
            dict containing:
                - modification_plan: The generated RepairPlan dict
                - ops_executed: int
                - success: bool
        """
        logger.info("RefinementAgent planning modifications for: %s", user_prompt[:80])

        # 1. Produce Modification Plan
        if self.mock_mode or not self.llm_service or not self.llm_service.config.api_key:
            plan = self._heuristic_refinements(user_prompt, scene_state)
        else:
            try:
                plan = await self._llm_generate_refinements(
                    user_prompt=user_prompt,
                    scene_state=scene_state,
                )
            except Exception as exc:
                logger.warning("LLM refinement planning failed (%s), using heuristic", exc)
                plan = self._heuristic_refinements(user_prompt, scene_state)

        # 2. Execute Modification Plan
        logger.info("Executing %d modification steps.", len(plan.steps))
        ops_executed = 0
        success = True

        if not self.mock_mode:
            for step in plan.steps:
                logger.info("  Modification step: %s on %s (Reason: %s)", step.corrective_operation, step.affected_object, step.reason)
                try:
                    result = await self.mcp_server.call_tool(step.corrective_operation, step.parameters)
                    if result.get("success", False):
                        ops_executed += 1
                    else:
                        logger.error("  Modification step failed: %s", result)
                        success = False
                except Exception as e:
                    logger.error("  Modification step raised exception: %s", e)
                    success = False

        return {
            "success": success,
            "ops_executed": ops_executed,
            "modification_plan": plan.model_dump(),
        }

    async def _llm_generate_refinements(
        self,
        user_prompt: str,
        scene_state: dict[str, Any],
    ) -> RepairPlan:
        """Ask the LLM to generate a targeted RepairPlan for the modification."""
        user_msg = (
            f"User Modification Request: {user_prompt}\n"
            f"Current Scene State: {json.dumps(scene_state)}\n\n"
            "Generate a targeted RepairPlan."
        )

        response = await self.llm_service.generate(
            prompt=user_msg,
            system_prompt=_REFINEMENT_SYSTEM_PROMPT.strip(),
            response_format={"type": "json_object"},
        )

        if not response:
            raise ValueError("Empty LLM response")

        clean = re.sub(r"^```json\s*|\s*```$", "", response.strip(), flags=re.MULTILINE)
        parsed = json.loads(clean)

        return RepairPlan.model_validate(parsed)

    def _heuristic_refinements(
        self,
        user_prompt: str,
        scene_state: dict[str, Any],
    ) -> RepairPlan:
        """Rule-based fallback modification plan."""
        steps = []
        lower = user_prompt.lower()
        
        objects = scene_state.get("objects", [])
        
        # Simple heuristic: if user says "blue", turn the first object blue
        if "blue" in lower and objects:
            obj_name = objects[0].get("name", "Unknown")
            mat_name = "BlueMat"
            steps.append(RepairStep(
                affected_object=mat_name,
                problem="User requested blue color",
                corrective_operation="create_material",
                parameters={"name": mat_name, "base_color": [0.0, 0.0, 1.0, 1.0]},
                reason="Create requested material"
            ))
            steps.append(RepairStep(
                affected_object=obj_name,
                problem="Apply new color",
                corrective_operation="assign_material",
                parameters={"object_name": obj_name, "material_name": mat_name},
                reason="Assign requested material to object"
            ))
            
        elif "taller" in lower and objects:
            obj_name = objects[0].get("name", "Unknown")
            steps.append(RepairStep(
                affected_object=obj_name,
                problem="User requested taller object",
                corrective_operation="set_transform",
                parameters={"object_name": obj_name, "scale": [1.0, 1.0, 1.5]},
                reason="Scale Z axis to make object taller"
            ))
            
        # Default fallback if empty
        if not steps:
            steps.append(RepairStep(
                affected_object="Scene",
                problem="Unknown modification requested",
                corrective_operation="setup_studio_lighting",
                parameters={"key_energy": 1200.0},
                reason="Fallback operation"
            ))

        return RepairPlan(steps=steps)
