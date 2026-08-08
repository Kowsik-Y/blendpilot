"""
BlendPilot AI — Step-by-Step Modeling Plan Agent

Workflow 4: Converts structured IntentSpec into an ordered ModelingPlan.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError
from schemas.intent import IntentSpec
from schemas.plan_state import ModelingPlan, ModelingStep, VALID_OPERATIONS
from services.llm import LLMService

logger = logging.getLogger("blendpilot.agents.planning")


class PlanningAgent:
    """Agent that creates structured, step-by-step ModelingPlans."""

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    async def execute(
        self,
        intent: IntentSpec | Any = None,
        spec: Any = None,
    ) -> ModelingPlan:
        """Generate a complete ModelingPlan from IntentSpec."""
        target_intent = intent if intent is not None else spec
        # Coerce DesignSpec/dict to IntentSpec for backward compatibility
        if not isinstance(target_intent, IntentSpec):
            if hasattr(target_intent, "model_dump"):
                intent_data = target_intent.model_dump()
            else:
                intent_data = target_intent
            target_intent = IntentSpec.model_validate(intent_data)

        intent = target_intent

        logger.info("Generating modeling plan for object type: %s...", intent.object_type)

        # Try LLM-powered plan generation if API key is configured
        if self.llm_service and self.llm_service.config.api_key:
            try:
                plan = await self._llm_generate_plan(intent)
                if plan and len(plan.steps) > 0:
                    logger.info("LLM generated %d-step plan for %s", len(plan.steps), intent.object_type)
                    return plan
            except Exception as e:
                logger.warning("LLM planning failed (%s), using procedural plan generator", e)

        # Fallback to procedural plan generator
        return self._generate_procedural_plan(intent)

    async def _llm_generate_plan(self, intent: IntentSpec) -> ModelingPlan | None:
        """Use LLM to generate ModelingPlan."""
        chat_model = self.llm_service.get_chat_model()
        structured_model = chat_model.with_structured_output(ModelingPlan)

        system_prompt = (
            "You are the Planning Agent for BlendPilot AI. "
            "Your role is to translate a structured design Intent (IntentSpec) into a sequential, "
            "ordered list of atomic ModelingSteps (ModelingPlan). "
            "Do not output any Python code. "
            f"Allowed operations: {', '.join(sorted(VALID_OPERATIONS))}."
        )

        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=intent.model_dump_json(indent=2)),
        ]

        result = await structured_model.ainvoke(messages)
        if result and isinstance(result, ModelingPlan):
            return result
        return None

    def _generate_procedural_plan(self, intent: IntentSpec) -> ModelingPlan:
        """Generates a fallback procedural ModelingPlan for supported categories."""
        steps: list[ModelingStep] = []
        obj_type = intent.object_type
        mat_name = intent.material or "default_material"
        color = intent.color or "gray"

        # Determine color RGBA values
        rgba = [0.8, 0.8, 0.8, 1.0]
        if color == "red":
            rgba = [0.9, 0.1, 0.1, 1.0]
        elif color == "green":
            rgba = [0.1, 0.8, 0.1, 1.0]
        elif color == "blue":
            rgba = [0.1, 0.1, 0.9, 1.0]
        elif color == "brown":
            rgba = [0.4, 0.25, 0.15, 1.0]
        elif color == "gold":
            rgba = [0.9, 0.7, 0.1, 1.0]

        # 1. Create Main primitive
        step_id = 1
        prim_type = "cube"
        if obj_type in ["mug", "bottle", "lamp"]:
            prim_type = "cylinder"

        steps.append(
            ModelingStep(
                step_id=step_id,
                operation="create_primitive",
                target=f"{obj_type}_base",
                parameters={
                    "primitive_type": prim_type,
                    "location": [0.0, 0.0, 0.5],
                    "dimensions": [1.0, 1.0, 1.0],
                },
            )
        )

        # 2. Add extra components
        leg_step_ids = []
        if obj_type in ["table", "chair", "stool", "desk"]:
            # Add 4 legs
            leg_positions = [
                [0.4, 0.4, 0.25],
                [-0.4, 0.4, 0.25],
                [0.4, -0.4, 0.25],
                [-0.4, -0.4, 0.25],
            ]
            for idx, pos in enumerate(leg_positions, 1):
                step_id += 1
                leg_name = f"leg_{idx}"
                steps.append(
                    ModelingStep(
                        step_id=step_id,
                        operation="create_primitive",
                        target=leg_name,
                        parameters={
                            "primitive_type": "cylinder",
                            "location": pos,
                            "dimensions": [0.1, 0.1, 0.5],
                        },
                        dependencies=[1],
                    )
                )
                leg_step_ids.append(step_id)

        # 3. Create Material
        step_id += 1
        mat_step_id = step_id
        steps.append(
            ModelingStep(
                step_id=step_id,
                operation="create_material",
                target=mat_name,
                parameters={
                    "base_color": rgba,
                    "metallic": 0.8 if mat_name in ["metal", "metallic", "gold", "silver"] else 0.0,
                    "roughness": 0.2 if mat_name in ["glass", "plastic"] else 0.5,
                },
            )
        )

        # 4. Assign Material
        step_id += 1
        steps.append(
            ModelingStep(
                step_id=step_id,
                operation="assign_material",
                target=f"{obj_type}_base",
                parameters={"material_name": mat_name},
                dependencies=[1, mat_step_id],
            )
        )

        for leg_step in leg_step_ids:
            step_id += 1
            steps.append(
                ModelingStep(
                    step_id=step_id,
                    operation="assign_material",
                    target=f"leg_{leg_step - 1}",
                    parameters={"material_name": mat_name},
                    dependencies=[leg_step, mat_step_id],
                )
            )

        # 5. Add Modifier
        if "bevel" in intent.additional_constraints or intent.style == "low-poly":
            step_id += 1
            steps.append(
                ModelingStep(
                    step_id=step_id,
                    operation="add_modifier",
                    target=f"{obj_type}_base",
                    parameters={"modifier_type": "BEVEL", "name": "Bevel"},
                    dependencies=[1],
                )
            )

        # 6. Camera / Lighting & Render
        step_id += 1
        steps.append(
            ModelingStep(
                step_id=step_id,
                operation="setup_preview_camera",
                target="Camera",
                parameters={"location": [2.5, -2.5, 2.0]},
            )
        )

        step_id += 1
        steps.append(
            ModelingStep(
                step_id=step_id,
                operation="setup_studio_lighting",
                target="Light",
                parameters={"type": "SUN", "energy": 5.0},
            )
        )

        step_id += 1
        steps.append(
            ModelingStep(
                step_id=step_id,
                operation="render_preview",
                target="Render",
                parameters={"output_path": f"output/{obj_type}/preview.png"},
            )
        )

        return ModelingPlan(steps=steps)
