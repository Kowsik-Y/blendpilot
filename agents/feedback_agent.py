"""
BlendPilot — Human Review & Feedback Agent

Workflow 9: Manages human-in-the-loop review interrupts, processes interactive chat
or email feedback, and converts change requests into structured revision plans.
"""

from __future__ import annotations

import logging
from typing import Any

from schemas.design import DesignSpec
from schemas.plan import DesignPlan, PlanStep, StepStatus

logger = logging.getLogger("blendpilot.agents.feedback")


class FeedbackAgent:
    """Agent that interprets human review feedback and translates comments into revision steps."""

    async def execute(
        self,
        spec: DesignSpec,
        plan: DesignPlan,
        feedback_text: str | None = None,
        action: str = "APPROVE",
    ) -> dict[str, Any]:
        """Process human review decision."""
        logger.info(
            "Processing human feedback: action=%s, feedback=%s", action, feedback_text)

        action_upper = action.upper().strip()
        if action_upper in ["APPROVE", "APPROVED", "PASS", "YES"]:
            return {
                "status": "APPROVED",
                "approved": True,
                "feedback_text": feedback_text or "Asset approved by human reviewer",
                "revision_plan": None,
            }

        # Human requested changes
        revision_steps: list[PlanStep] = []
        fb_lower = (feedback_text or "").lower()

        target_obj = f"{spec.asset_type.capitalize()}_Main"

        if "taller" in fb_lower or "height" in fb_lower:
            spec.dimensions.height *= 1.25
            revision_steps.append(PlanStep(
                step_id=201,
                description=f"Adjust height transform on {target_obj}",
                tool="set_transform",
                parameters={"name": target_obj, "scale": [1.0, 1.0, 1.25]},
                expected_outcome="Height scaled up by 25%",
            ))
        elif "wider" in fb_lower or "width" in fb_lower:
            spec.dimensions.width *= 1.2
            revision_steps.append(PlanStep(
                step_id=202,
                description=f"Adjust width transform on {target_obj}",
                tool="set_transform",
                parameters={"name": target_obj, "scale": [1.2, 1.0, 1.0]},
                expected_outcome="Width scaled up by 20%",
            ))
        elif "brighter" in fb_lower or "glow" in fb_lower:
            revision_steps.append(PlanStep(
                step_id=203,
                description="Increase emission brightness",
                tool="create_material",
                parameters={
                    "name": f"Mat_{spec.asset_type}_EmissiveBlue",
                    "emission_strength": 12.0,
                },
                expected_outcome="Emission strength doubled to 12.0",
            ))
        else:
            # General refinement step
            revision_steps.append(PlanStep(
                step_id=204,
                description=f"Refine bevel smoothness for {target_obj}",
                tool="add_modifier",
                parameters={
                    "object_name": target_obj,
                    "modifier_type": "BEVEL",
                    "properties": {"width": 0.04, "segments": 3},
                },
                expected_outcome="Enhanced bevel highlights",
            ))

        revision_plan = DesignPlan(
            spec_id=f"revision_{spec.asset_type}",
            steps=revision_steps,
            current_step_index=0,
            status=StepStatus.PENDING,
        )

        return {
            "status": "REVISION_REQUESTED",
            "approved": False,
            "feedback_text": feedback_text,
            "revision_plan": revision_plan,
        }
