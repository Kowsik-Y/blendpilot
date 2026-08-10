"""
BlendPilot AI — Step-by-Step Design Planning Agent

Workflow 4: Uses LLM to generate creative, context-aware modeling plans that
leverage the full MCP tool registry. Falls back to enhanced procedural plans.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from prompts.planning import PLANNING_SYSTEM_PROMPT, PLANNING_USER_PROMPT
from schemas.design import DesignSpec
from schemas.plan import DesignPlan, PlanStep, StepStatus
from schemas.scene import SceneSummary
from services.llm import LLMService

logger = logging.getLogger("blendpilot.agents.planning")

# Available MCP tools the LLM can use in its plan
MCP_TOOLS_CONTEXT = """
Available Blender MCP Tools (use these exact tool names in plan steps):
- create_primitive: Create a mesh (cube, cylinder, uv_sphere, ico_sphere, plane, cone, torus) with name, dimensions [w,d,h], location [x,y,z]
- set_transform: Set location/rotation/scale of an existing object
- duplicate_object: Duplicate an object with optional offset [x,y,z]
- delete_object: Delete an object by name
- add_modifier: Add modifier (BEVEL, SUBSURF, SOLIDIFY, MIRROR, BOOLEAN, DECIMATE, EDGE_SPLIT) with properties
- apply_modifier: Bake a modifier into the mesh
- edit_mesh: Perform mesh operations (recalculate_normals, subdivide, bevel_edges)
- create_material: Create PBR material with base_color [r,g,b,a], metallic, roughness, emission_color, emission_strength
- assign_material: Assign material to object
- save_checkpoint: Save a .blend checkpoint for rollback
"""


class PlanningAgent:
    """Agent that creates structured, step-by-step 3D modeling plans using LLM reasoning."""

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    async def execute(
        self,
        spec: DesignSpec,
        scene: SceneSummary | None = None,
        research: list[dict[str, Any]] | None = None,
    ) -> DesignPlan:
        """Generate a complete DesignPlan from DesignSpec."""
        logger.info("Generating design plan for %s...", spec.asset_type)

        # Strict LLM-powered plan generation
        try:
            plan = await self._llm_generate_plan(spec, scene, research)
            if plan and len(plan.steps) > 0:
                logger.info("LLM generated %d-step plan for %s", len(plan.steps), spec.asset_type)
                return plan
        except Exception as e:
            logger.error("LLM planning failed (%s)", e)
            raise RuntimeError(f"Failed to generate DesignPlan via LLM: {e}")

        raise RuntimeError("LLM failed to return a valid DesignPlan and no fallback is permitted.")

    async def _llm_generate_plan(
        self,
        spec: DesignSpec,
        scene: SceneSummary | None,
        research: list[dict[str, Any]] | None,
    ) -> DesignPlan | None:
        """Use LLM to generate creative, context-aware modeling plans."""
        try:
            system_prompt = PLANNING_SYSTEM_PROMPT.format(
                format_instructions=(
                    "Return a JSON object with this structure:\n"
                    '{"spec_id": "plan_<asset_type>", "steps": [...], "current_step_index": 0, "status": "pending"}\n'
                    "Each step: {\"step_id\": int, \"description\": str, \"tool\": str, "
                    "\"parameters\": {}, \"dependencies\": [int], \"expected_outcome\": str}\n\n"
                    + MCP_TOOLS_CONTEXT
                )
<<<<<<< HEAD
                user_msg = PLANNING_USER_PROMPT.format(
                    design_spec=spec.model_dump_json(indent=2),
                    scene_summary=scene.model_dump_json(indent=2) if scene else "{}",
                    research_results=json.dumps(research or []),
                )
                response = await self.llm_service.generate(
                    prompt=user_msg,
                    system_prompt=system_prompt,
                    response_format={"type": "json_object"},
                )
                clean_json = response.strip()
                json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_json)
                if json_match:
                    clean_json = json_match.group(1).strip()
                else:
                    brace_match = re.search(r"(\{[\s\S]*\})", clean_json)
                    if brace_match:
                        clean_json = brace_match.group(1).strip()

                data = json.loads(clean_json)
                if isinstance(data, list):
                    data = {"steps": data}
                return DesignPlan.model_validate(data)
            except Exception as e:
                logger.warning("LLM planning failed (%s), using robust procedural plan generator", e)
=======
            )
            user_msg = PLANNING_USER_PROMPT.format(
                design_spec=spec.model_dump_json(indent=2),
                scene_summary=scene.model_dump_json(indent=2) if scene else "{}",
                research_results=json.dumps(research or []),
            )
            # Tool planning must never hold the workflow indefinitely. A
            # timeout falls through to the validated procedural fallback so
            # the modeler can start creating the requested asset.
            response = await asyncio.wait_for(
                self.llm_service.generate(
                    prompt=user_msg,
                    system_prompt=system_prompt,
                    response_format={"type": "json_object"},
                ),
                timeout=20,
            )
>>>>>>> 9960c34c885b76ae6a6056cb373b1205a98fc89e

            if not response:
                return None

            clean_json = re.sub(r"^```json\s*|\s*```$", "", response.strip(), flags=re.MULTILINE)
            data = json.loads(clean_json)

            # Validate and normalize the LLM output
            if "steps" not in data:
                return None

            return DesignPlan.model_validate(data)

        except Exception as e:
            logger.warning("LLM plan generation failed: %s", e)
            return None


