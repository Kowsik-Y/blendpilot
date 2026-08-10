"""
BlendPilot AI - Unified Blender Generation Agent

Workflow 5: Translates a validated ModelingPlan into direct Blender core operations.
"""

from __future__ import annotations

import logging
from typing import Any

from schemas.plan_state import ModelingPlan, ModelingStep, StepExecution, PlanExecution
from schemas.plan import StepStatus
from services.llm import LLMService

logger = logging.getLogger("blendpilot.agents.generation")


class GenerationAgent:
    """Agent that translates ModelingPlan steps into direct Blender core operations."""

    def __init__(
        self,
        mcp_server: Any | None = None,
        llm_service: LLMService | None = None,
        mock_mode: bool = False,
    ):
        self.mcp_server = mcp_server
        self.llm_service = llm_service
        self.mock_mode = mock_mode
        if mcp_server and getattr(getattr(mcp_server, "client", None), "mock_mode", False):
            self.mock_mode = True

    def translate(self, plan: ModelingPlan | Any) -> list[dict[str, Any]]:
        """Translate a ModelingPlan into a list of serialized core operations."""
        if not isinstance(plan, ModelingPlan):
            steps = []
            for step in getattr(plan, "steps", []):
                steps.append(
                    ModelingStep(
                        step_id=step.step_id,
                        operation=step.tool or step.required_tool or step.operation,
                        target=step.target_object or step.target or "",
                        parameters=step.parameters or {},
                        dependencies=step.dependencies or [],
                    )
                )
            plan = ModelingPlan(steps=steps)

        return [step.model_dump() for step in plan.steps]

    async def execute(
        self,
        spec: Any,
        plan: ModelingPlan | Any,
        output_image_path: str | None = None,
    ) -> dict[str, Any]:
        """Run the full generation pipeline by executing ModelingPlan steps."""
        # Coerce DesignPlan to ModelingPlan if needed
        if not isinstance(plan, ModelingPlan):
            steps = []
            for step in getattr(plan, "steps", []):
                steps.append(
                    ModelingStep(
                        step_id=step.step_id,
                        operation=step.tool or step.required_tool,
                        target=step.target_object or "",
                        parameters=step.parameters or {},
                        dependencies=step.dependencies or [],
                    )
                )
            plan = ModelingPlan(steps=steps)

        asset_type = getattr(spec, "asset_type", getattr(spec, "object_type", "object"))
        if output_image_path is None:
            output_image_path = f"output/{asset_type}/preview.png"

        logger.info("GenerationAgent starting execution for '%s' - %d plan steps", asset_type, len(plan.steps))

        created_objects: list[str] = []
        materials_created: list[str] = []
        step_executions: list[StepExecution] = []
        all_success = True

        for step in plan.steps:
            logger.info("Executing Step %d: [%s] on target: %s", step.step_id, step.operation, step.target)

            success = False
            msg = ""
            details = {}

            if self.mock_mode:
                success = True
                msg = f"Mock execution of {step.operation} succeeded"
                details = {"mocked": True}
            else:
                try:
                    res = await self._execute_core_operation(step, output_image_path)
                    success = res.get("success", False)
                    msg = res.get("message") or res.get("error") or ""
                    details = res
                except Exception as e:
                    logger.exception("Step %d execution failed with exception", step.step_id)
                    success = False
                    msg = str(e)
                    details = {"exception": str(e)}

            if success:
                if step.operation in ["create_primitive", "duplicate_object"]:
                    obj_name = details.get("object_name") or details.get("new_object") or step.target
                    if obj_name and obj_name not in created_objects:
                        created_objects.append(obj_name)
                elif step.operation == "create_material":
                    mat_name = details.get("material_name") or step.target
                    if mat_name and mat_name not in materials_created:
                        materials_created.append(mat_name)
            else:
                all_success = False

            step_executions.append(
                StepExecution(
                    step_id=step.step_id,
                    operation=step.operation,
                    target=step.target,
                    success=success,
                    message=msg,
                    details=details,
                )
            )

        execution_result = PlanExecution(
            success=all_success,
            created_objects=created_objects,
            materials_created=materials_created,
            step_executions=step_executions,
            preview_image_path=output_image_path,
        )

        return execution_result.model_dump()

    async def _execute_core_operation(self, step: ModelingStep, default_output_path: str) -> dict[str, Any]:
        """Execute a single core Blender operation by routing to the MCP Server.

        Normalizes LLM-generated parameter field names to match the canonical
        MCP tool schemas defined in mcp_servers/blender/schemas.py.
        """
        op = step.operation
        params = dict(step.parameters or {})

        if op == "create_primitive":
            # Schema: primitive_type (not "type"), name
            if "primitive_type" not in params and "type" in params:
                params["primitive_type"] = params.pop("type")
            if "name" not in params:
                params["name"] = step.target

        elif op in ("set_transform", "duplicate_object", "delete_object"):
            # Schema: name (not "object_name")
            if "name" not in params:
                params["name"] = params.pop("object_name", step.target)
            elif "object_name" in params:
                params.pop("object_name", None)

        elif op == "assign_material":
            # Schema: object_name, material_name (not "material")
            if "material_name" not in params and "material" in params:
                params["material_name"] = params.pop("material")
            if "object_name" not in params:
                params["object_name"] = step.target

        elif op in ("add_modifier", "apply_modifier"):
            # Schema: object_name
            if "object_name" not in params:
                params["object_name"] = params.pop("name", step.target)

        elif op == "create_material":
            # Schema: name
            if "name" not in params:
                params["name"] = step.target

        elif op == "edit_mesh":
            # Schema: object_name, operation
            if "object_name" not in params:
                params["object_name"] = params.pop("name", step.target)
            if "operation" not in params:
                # LLM often sends mesh_type instead of operation
                mesh_type = params.pop("mesh_type", "")
                op_map = {
                    "low-poly": "recalculate_normals",
                    "low_poly": "recalculate_normals",
                    "smooth": "smooth_normals",
                    "bevel": "bevel",
                    "subdivide": "subdivide",
                    "decimate": "decimate",
                }
                params["operation"] = op_map.get(mesh_type, "recalculate_normals")

        elif op == "render_preview":
            # Schema: output_path
            if "output_path" not in params:
                params["output_path"] = default_output_path

        elif op in ("save_checkpoint", "save_project", "restore_checkpoint"):
            # Schema: filepath
            if "filepath" not in params:
                alt = params.pop("path", params.pop("file", "output/checkpoint.blend"))
                params["filepath"] = alt

        elif op == "export_asset":
            # Schema: object_names (list), output_path
            if "object_names" not in params and "object_name" in params:
                params["object_names"] = [params.pop("object_name")]
            if "output_path" not in params:
                params["output_path"] = params.pop("path", "output/export.fbx")

        if not self.mcp_server:
            from mcp_servers.blender.server import BlenderMCPServer
            self.mcp_server = BlenderMCPServer()

        logger.info("Routing '%s' through MCP Server with params %s", op, params)
        result = await self.mcp_server.call_tool(op, params)

        # Flatten nested result dicts from call_tool
        if "result" in result and isinstance(result["result"], dict):
            out = dict(result["result"])
            out["success"] = result.get("success", False)
            out["message"] = result.get("error", "") or out.get("message", "")
            return out
        return result
