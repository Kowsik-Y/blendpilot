"""
BlendPilot AI — Deterministic Geometry QA Agent

Workflow 7: Runs deterministic checks (triangle count, manifold geometry, normals, transforms, origins, missing objects)
and generates a structured ValidationReport.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp_servers.blender.server import BlenderMCPServer
from schemas.design import DesignSpec
from schemas.plan_state import ModelingPlan
from schemas.validation import QACheckResult, ValidationReport

logger = logging.getLogger("blendpilot.agents.geometry_qa")


class GeometryQAAgent:
    """Agent that performs deterministic topology inspection."""

    def __init__(self, mcp_server: BlenderMCPServer | None = None):
        self.mcp_server = mcp_server or BlenderMCPServer()

    async def execute(
        self,
        spec: DesignSpec,
        plan: ModelingPlan,
        created_objects: list[str],
    ) -> dict[str, Any]:
        """Validate all created geometry against spec constraints and return QA status."""
        logger.info("Running deterministic Geometry QA on %s...", created_objects)

        checks: list[QACheckResult] = []
        overall_passed = True

        # 1. Missing objects check
        expected_objects = []
        for step in plan.steps:
            if getattr(step, "tool", getattr(step, "operation", "")) in ["create_primitive", "import_mesh", "create_mesh"]:
                if "object_name" in step.parameters:
                    expected_objects.append(step.parameters["object_name"])
                elif "name" in step.parameters:
                    expected_objects.append(step.parameters["name"])
                elif getattr(step, "target", None):
                    expected_objects.append(step.target)
        
        # Unique expected objects
        expected_objects = list(set(expected_objects))

        for obj in expected_objects:
            if obj not in created_objects:
                checks.append(QACheckResult(
                    passed=False,
                    severity="critical",
                    check_name="missing_required_object",
                    object=obj,
                    message=f"Expected object '{obj}' was not created or found in the scene.",
                    suggested_action="Check planner/generator to ensure the object is created."
                ))
                overall_passed = False

        # 2. Asset validation per created object
        for obj_name in created_objects:
            res = await self.mcp_server.call_tool("validate_asset", {
                "object_name": obj_name,
                "triangle_limit": spec.triangle_limit,
                "target_engine": spec.target_platform,
            })

            if not res.get("success") or res.get("passed") is False:
                overall_passed = False
            
            result_data = res.get("result", {})
            obj_checks = result_data.get("checks", [])
            if obj_checks:
                for chk in obj_checks:
                    checks.append(QACheckResult.model_validate(chk))
            elif not res.get("success"):
                checks.append(QACheckResult(
                    passed=False,
                    severity="critical",
                    check_name="validation_execution_error",
                    object=obj_name,
                    message=res.get("error", "Unknown validation execution error."),
                    suggested_action="Review blender logs."
                ))

        report = ValidationReport(
            passed=overall_passed,
            checks=checks,
        )

        return {
            "status": "PASS" if overall_passed else "FAIL",
            "passed": overall_passed,
            "validation_report": report.model_dump(),
        }
