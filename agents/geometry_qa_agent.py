"""
BlendPilot AI — Deterministic Geometry QA Agent

Workflow 7: Runs deterministic checks (triangle count, manifold geometry, normals, transforms, origins)
and generates targeted repair plans if validation fails.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp_servers.blender.server import BlenderMCPServer
from schemas.design import DesignSpec
from schemas.plan import PlanStep
from schemas.validation import IssueSeverity, ValidationIssue, ValidationResult

logger = logging.getLogger("blendpilot.agents.geometry_qa")


class GeometryQAAgent:
    """Agent that performs deterministic topology inspection and generates repair loops."""

    def __init__(self, mcp_server: BlenderMCPServer | None = None):
        self.mcp_server = mcp_server or BlenderMCPServer()

    async def execute(
        self,
        spec: DesignSpec,
        created_objects: list[str],
        repair_iteration: int = 0,
    ) -> dict[str, Any]:
        """Validate all created geometry against spec constraints and return QA status with repair actions if needed."""
        logger.info("Running deterministic Geometry QA (iteration %d) on %s...", repair_iteration, created_objects)

        issues: list[ValidationIssue] = []
        overall_status = "PASS"

        for obj_name in created_objects:
            res = await self.mcp_server.call_tool("validate_asset", {
                "object_name": obj_name,
                "triangle_limit": spec.triangle_limit,
                "target_engine": spec.target_platform,
            })

            if not res.get("success") or res.get("status") == "FAIL":
                result_data = res.get("result", {})
                obj_issues = result_data.get("issues", [])
                if obj_issues:
                    for iss in obj_issues:
                        if isinstance(iss, dict):
                            issues.append(ValidationIssue.model_validate(iss))
                        elif isinstance(iss, ValidationIssue):
                            issues.append(iss)
                else:
                    issues.append(ValidationIssue(
                        type="TOPOLOGY_ERROR",
                        description=res.get("error", f"Validation failed on {obj_name}"),
                        severity=IssueSeverity.MEDIUM,
                        object_name=obj_name,
                    ))
                overall_status = "FAIL"

        # Calculate geometric QA score
        score = 1.0
        for iss in issues:
            if iss.severity == IssueSeverity.CRITICAL:
                score -= 0.4
            elif iss.severity == IssueSeverity.HIGH:
                score -= 0.25
            elif iss.severity == IssueSeverity.MEDIUM:
                score -= 0.1
            else:
                score -= 0.05
        score = max(0.0, min(1.0, score))

        # Generate automated repair plan steps if QA failed
        repair_steps: list[PlanStep] = []
        if overall_status == "FAIL" and repair_iteration < 3:
            for i, iss in enumerate(issues, start=1):
                target = iss.object_name or (created_objects[0] if created_objects else "Object")
                if "normal" in iss.type.lower() or "normal" in iss.description.lower():
                    repair_steps.append(PlanStep(
                        step_id=100 + i,
                        description=f"Recalculate face normals for {target}",
                        tool="edit_mesh",
                        parameters={"object_name": target, "operation": "recalculate_normals"},
                        expected_outcome="Face normals outward pointing and consistent",
                    ))
                elif "triangle" in iss.type.lower() or "budget" in iss.description.lower():
                    repair_steps.append(PlanStep(
                        step_id=100 + i,
                        description=f"Decimate mesh {target} to satisfy triangle budget",
                        tool="add_modifier",
                        parameters={
                            "object_name": target,
                            "modifier_type": "DECIMATE",
                            "modifier_name": "QADecimate",
                            "properties": {"ratio": 0.75},
                        },
                        expected_outcome="Triangle count reduced by 25%",
                    ))
                elif "transform" in iss.type.lower():
                    repair_steps.append(PlanStep(
                        step_id=100 + i,
                        description=f"Bake transform matrix on {target}",
                        tool="edit_mesh",
                        parameters={"object_name": target, "operation": "apply_transforms"},
                        expected_outcome="Scale set to (1,1,1) with origin at base",
                    ))

        val_result = ValidationResult(
            status=overall_status,
            issues=issues,
            score=score,
        )

        return {
            "status": overall_status,
            "score": score,
            "validation_result": val_result,
            "repair_steps": repair_steps,
            "requires_repair": overall_status == "FAIL" and len(repair_steps) > 0 and repair_iteration < 3,
        }
