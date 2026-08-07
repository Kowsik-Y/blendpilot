"""
BlendPilot AI — Step-by-Step Design Planning Agent

Workflow 4: Deconstructs DesignSpec into an ordered, atomic sequence of PlanSteps.
"""

from __future__ import annotations

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


class PlanningAgent:
    """Agent that creates structured, step-by-step 3D modeling plans."""

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

        # Fallback procedural plan generator for deterministic reliability & testing
        fallback_plan = self._generate_procedural_plan(spec)

        # Use LLM if configured
        if self.llm_service and self.llm_service.config.api_key:
            try:
                system_prompt = PLANNING_SYSTEM_PROMPT.format(
                    format_instructions="Return a JSON matching the DesignPlan schema with steps."
                )
                user_msg = PLANNING_USER_PROMPT.format(
                    design_spec=spec.model_dump_json(indent=2),
                    scene_summary=scene.model_dump_json(indent=2) if scene else "{}",
                    research_notes=json.dumps(research or []),
                )
                response = await self.llm_service.generate(
                    prompt=user_msg,
                    system_prompt=system_prompt,
                    response_format={"type": "json_object"},
                )
                clean_json = re.sub(r"^```json\s*|\s*```$", "", response.strip(), flags=re.MULTILINE)
                data = json.loads(clean_json)
                return DesignPlan.model_validate(data)
            except Exception as e:
                logger.warning("LLM planning failed (%s), using robust procedural plan generator", e)

        return fallback_plan

    def _generate_procedural_plan(self, spec: DesignSpec) -> DesignPlan:
        """Generate a clean, structured plan for creating the asset in Blender."""
        steps: list[PlanStep] = []
        w, d, h = spec.dimensions.width, spec.dimensions.depth, spec.dimensions.height

        # 1. Main body / primary geometry
        main_name = f"{spec.asset_type.capitalize()}_Main"
        primitive = "cylinder" if spec.asset_type in ["barrel", "street_lamp", "piston", "robot_wheel", "pipe_valve"] else "cube"

        steps.append(PlanStep(
            step_id=1,
            description=f"Create primary blockout primitive for {spec.asset_type}",
            tool="create_primitive",
            parameters={
                "primitive_type": primitive,
                "name": main_name,
                "dimensions": [w, d, h],
                "location": [0.0, 0.0, h / 2.0],
            },
            expected_outcome=f"Primary {primitive} '{main_name}' centered on ground plane",
        ))

        # 2. Bevel modifier for realistic edge highlight
        steps.append(PlanStep(
            step_id=2,
            description="Add Bevel modifier for smooth edge reflections",
            tool="add_modifier",
            parameters={
                "object_name": main_name,
                "modifier_type": "BEVEL",
                "modifier_name": "EdgeBevel",
                "properties": {"width": 0.03, "segments": 2},
            },
            dependencies=[1],
            expected_outcome=f"Bevel modifier added to '{main_name}'",
        ))

        # 3. Apply Bevel
        steps.append(PlanStep(
            step_id=3,
            description="Apply bevel modifier into geometry",
            tool="apply_modifier",
            parameters={
                "object_name": main_name,
                "modifier_name": "EdgeBevel",
            },
            dependencies=[2],
            expected_outcome="Bevel baked into mesh",
        ))

        # 4. Secondary detail object (e.g. Lid, Base, Accent)
        accent_name = f"{spec.asset_type.capitalize()}_Accent"
        steps.append(PlanStep(
            step_id=4,
            description=f"Create accent detailing for {spec.asset_type}",
            tool="create_primitive",
            parameters={
                "primitive_type": "cube",
                "name": accent_name,
                "dimensions": [w * 1.04, d * 1.04, h * 0.15],
                "location": [0.0, 0.0, h * 0.9],
            },
            dependencies=[1],
            expected_outcome=f"Accent detail '{accent_name}' positioned near top",
        ))

        # 5. Checkpoint
        steps.append(PlanStep(
            step_id=5,
            description="Save blockout milestone checkpoint",
            tool="save_checkpoint",
            parameters={
                "filepath": f"output/checkpoints/{spec.asset_type}_blockout.blend",
                "checkpoint_name": "01_blockout_complete",
            },
            dependencies=[3, 4],
            expected_outcome="Blockout .blend checkpoint saved",
        ))

        return DesignPlan(
            spec_id=f"plan_{spec.asset_type}",
            steps=steps,
            current_step_index=0,
            status=StepStatus.PENDING,
        )
