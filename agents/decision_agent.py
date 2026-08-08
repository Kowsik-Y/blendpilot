"""
BlendPilot AI — Decision Agent

Phase 3: Evaluates aggregated QA signals (Geometry QA + Visual Critic) and
determines whether to APPROVE the asset for export or route it to the
Repair Agent for another correction loop.

The Decision Agent replaces the hardcoded route functions and the FeedbackAgent,
bringing LLM-driven reasoning into the routing decision.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from schemas.design import DesignSpec
from services.llm import LLMService

logger = logging.getLogger("blendpilot.agents.decision")

_DECISION_SYSTEM_PROMPT = """
You are the Quality Decision Agent for a BlendPilot 3D asset generation pipeline.

You receive signals from two validators:
1. Geometry QA Agent — deterministic checks (normals, manifold, triangle count, transforms)
2. Visual Critic Agent — aesthetic evaluation (silhouette, materials, lighting, appeal)

Your task: decide whether the 3D asset is ready to export, or whether it needs
another repair loop.

Rules:
- If geometry_qa_status == "FAIL" and repair_count < max_repairs → REPAIR
- If geometry_qa_status == "PASS" and visual_qa_approved == false and visual_revision_count < max_revisions → REPAIR
- If geometry_qa_status == "PASS" and visual_qa_approved == true → APPROVE
- If any max repair/revision limit is hit → APPROVE (accept current state and export)
- Always include a clear reason in your response.

Respond ONLY with a JSON object:
{
  "decision": "APPROVE" | "REPAIR",
  "reason": "<concise explanation>",
  "priority_issue": "geometry" | "visual" | "none"
}
"""


class DecisionAgent:
    """LLM-driven routing agent that decides APPROVE or REPAIR after validation."""

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    async def execute(
        self,
        spec: DesignSpec,
        geometry_qa_status: str,
        geometry_score: float,
        geometry_issues: list[dict[str, Any]],
        geometry_repair_count: int,
        max_geometry_repairs: int,
        visual_qa_approved: bool,
        visual_score: float,
        visual_issues: list[str],
        visual_revision_count: int,
        max_visual_revisions: int,
    ) -> dict[str, Any]:
        """Make an APPROVE or REPAIR decision based on current validation state.

        Returns:
            dict with keys: decision ("APPROVE" | "REPAIR"), reason, priority_issue
        """
        logger.info(
            "DecisionAgent evaluating — geo: %s (%.2f), visual: approved=%s (%.2f)",
            geometry_qa_status,
            geometry_score,
            visual_qa_approved,
            visual_score,
        )

        # Deterministic guard rails (always respected, even if LLM fails)
        if geometry_qa_status == "PASS" and visual_qa_approved:
            return {"decision": "APPROVE", "reason": "All validators approved.", "priority_issue": "none"}

        if geometry_repair_count >= max_geometry_repairs and visual_revision_count >= max_visual_revisions:
            return {
                "decision": "APPROVE",
                "reason": "Max repair/revision limits reached — exporting best available result.",
                "priority_issue": "none",
            }

        # Try LLM-powered decision when API key is available
        if self.llm_service and self.llm_service.config.api_key:
            try:
                return await self._llm_decide(
                    spec=spec,
                    geometry_qa_status=geometry_qa_status,
                    geometry_score=geometry_score,
                    geometry_issues=geometry_issues,
                    geometry_repair_count=geometry_repair_count,
                    max_geometry_repairs=max_geometry_repairs,
                    visual_qa_approved=visual_qa_approved,
                    visual_score=visual_score,
                    visual_issues=visual_issues,
                    visual_revision_count=visual_revision_count,
                    max_visual_revisions=max_visual_revisions,
                )
            except Exception as exc:
                logger.warning("LLM decision failed (%s), falling back to heuristic", exc)

        # Heuristic fallback
        return self._heuristic_decide(
            geometry_qa_status=geometry_qa_status,
            geometry_repair_count=geometry_repair_count,
            max_geometry_repairs=max_geometry_repairs,
            visual_qa_approved=visual_qa_approved,
            visual_revision_count=visual_revision_count,
            max_visual_revisions=max_visual_revisions,
        )

    async def _llm_decide(self, **kwargs: Any) -> dict[str, Any]:
        """Ask the LLM to evaluate the QA signals and return a decision."""
        spec: DesignSpec = kwargs["spec"]
        user_msg = (
            f"Asset: {spec.asset_type} (style: {spec.style}, platform: {spec.target_platform})\n\n"
            f"Geometry QA:\n"
            f"  status: {kwargs['geometry_qa_status']}\n"
            f"  score: {kwargs['geometry_score']:.2f}\n"
            f"  issues ({len(kwargs['geometry_issues'])}): {json.dumps(kwargs['geometry_issues'][:3])}\n"
            f"  repair_count: {kwargs['geometry_repair_count']} / {kwargs['max_geometry_repairs']}\n\n"
            f"Visual Critic:\n"
            f"  approved: {kwargs['visual_qa_approved']}\n"
            f"  score: {kwargs['visual_score']:.2f}\n"
            f"  issues: {kwargs['visual_issues']}\n"
            f"  revision_count: {kwargs['visual_revision_count']} / {kwargs['max_visual_revisions']}\n\n"
            "Make your APPROVE or REPAIR decision."
        )

        response = await self.llm_service.generate(
            prompt=user_msg,
            system_prompt=_DECISION_SYSTEM_PROMPT.strip(),
            response_format={"type": "json_object"},
        )

        if not response:
            raise ValueError("Empty LLM response")

        clean = re.sub(r"^```json\s*|\s*```$", "", response.strip(), flags=re.MULTILINE)
        data = json.loads(clean)

        decision = data.get("decision", "REPAIR")
        if decision not in ("APPROVE", "REPAIR"):
            decision = "REPAIR"

        return {
            "decision": decision,
            "reason": data.get("reason", ""),
            "priority_issue": data.get("priority_issue", "none"),
        }

    def _heuristic_decide(
        self,
        geometry_qa_status: str,
        geometry_repair_count: int,
        max_geometry_repairs: int,
        visual_qa_approved: bool,
        visual_revision_count: int,
        max_visual_revisions: int,
    ) -> dict[str, Any]:
        """Simple rule-based fallback decision."""
        if geometry_qa_status == "FAIL" and geometry_repair_count < max_geometry_repairs:
            return {
                "decision": "REPAIR",
                "reason": f"Geometry QA failed — attempting repair (attempt {geometry_repair_count + 1}/{max_geometry_repairs}).",
                "priority_issue": "geometry",
            }
        if not visual_qa_approved and visual_revision_count < max_visual_revisions:
            return {
                "decision": "REPAIR",
                "reason": f"Visual critique not approved — attempting aesthetic refinement (revision {visual_revision_count + 1}/{max_visual_revisions}).",
                "priority_issue": "visual",
            }
        return {
            "decision": "APPROVE",
            "reason": "Validation complete or limits reached — approving for export.",
            "priority_issue": "none",
        }
