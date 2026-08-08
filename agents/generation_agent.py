"""
BlendPilot AI — Unified Blender Generation Agent

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
        """Run the full generation pipeline by executing ModelingPlan steps.

        Args:
            spec: The design spec (DesignSpec or IntentSpec).
            plan: The modeling plan (ModelingPlan or DesignPlan).
            output_image_path: Path to write the preview render to.

        Returns:
            dict matching PlanExecution structure.
        """
        # Coerce DesignPlan to ModelingPlan if needed
        if not isinstance(plan, ModelingPlan):
            steps = []
            for step in getattr(plan, "steps", []):
                # Map PlanStep to ModelingStep
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

        logger.info("GenerationAgent starting execution for '%s' — %d plan steps", asset_type, len(plan.steps))

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
                # Simulated/mock mode to bypass Blender environment
                success = True
                msg = f"Mock execution of {step.operation} succeeded"
                details = {"mocked": True}
            else:
                try:
                    res = self._execute_core_operation(step, output_image_path)
                    success = res.get("success", False)
                    msg = res.get("message", "")
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

    def _execute_core_operation(self, step: ModelingStep, default_output_path: str) -> dict[str, Any]:
        """Execute a single core Blender operation by calling deterministic functions in core/."""
        import core.objects
        import core.materials
        import core.modifiers
        import core.rendering
        import core.project

        op = step.operation
        params = step.parameters or {}

        if op == "create_primitive":
            prim_type = params.get("primitive_type") or "cube"
            name = params.get("name") or step.target
            dims = params.get("dimensions")
            if isinstance(dims, list):
                dims = tuple(dims)
            loc = params.get("location") or (0.0, 0.0, 0.0)
            if isinstance(loc, list):
                loc = tuple(loc)
            rot = params.get("rotation") or (0.0, 0.0, 0.0)
            if isinstance(rot, list):
                rot = tuple(rot)
            return core.objects.create_primitive(
                primitive_type=prim_type,
                name=name,
                dimensions=dims,
                location=loc,
                rotation=rot,
            )

        elif op == "set_transform":
            name = params.get("object_name") or step.target
            loc = params.get("location")
            if isinstance(loc, list):
                loc = tuple(loc)
            rot = params.get("rotation")
            if isinstance(rot, list):
                rot = tuple(rot)
            sc = params.get("scale")
            if isinstance(sc, list):
                sc = tuple(sc)
            return core.objects.set_transform(
                name=name,
                location=loc,
                rotation=rot,
                scale=sc,
            )

        elif op == "duplicate_object":
            name = params.get("object_name") or step.target
            new_name = params.get("new_name") or f"{name}_dup"
            offset = params.get("offset") or (0.0, 0.0, 0.0)
            if isinstance(offset, list):
                offset = tuple(offset)
            return core.objects.duplicate_object(
                name=name,
                new_name=new_name,
                offset=offset,
            )

        elif op == "delete_object":
            name = params.get("object_name") or step.target
            return core.objects.delete_object(name=name)

        elif op == "create_material":
            name = params.get("name") or step.target
            base_color = params.get("base_color") or (0.8, 0.8, 0.8, 1.0)
            if isinstance(base_color, list):
                base_color = tuple(base_color)
            met = params.get("metallic", 0.0)
            rough = params.get("roughness", 0.5)
            em_color = params.get("emission_color")
            if isinstance(em_color, list):
                em_color = tuple(em_color)
            em_str = params.get("emission_strength", 0.0)
            return core.materials.create_material(
                name=name,
                base_color=base_color,
                metallic=met,
                roughness=rough,
                emission_color=em_color,
                emission_strength=em_str,
            )

        elif op == "assign_material":
            obj_name = params.get("object_name") or step.target
            mat_name = params.get("material_name") or ""
            return core.materials.assign_material(
                object_name=obj_name,
                material_name=mat_name,
            )

        elif op == "add_modifier":
            obj_name = params.get("object_name") or step.target
            mod_type = params.get("modifier_type") or "BEVEL"
            name = params.get("name") or "Bevel"
            props = params.get("properties") or params.get("params")
            return core.modifiers.add_modifier(
                object_name=obj_name,
                modifier_type=mod_type,
                modifier_name=name,
                params=props,
            )

        elif op == "apply_modifier":
            obj_name = params.get("object_name") or step.target
            mod_name = params.get("modifier_name") or ""
            return core.modifiers.apply_modifier(
                object_name=obj_name,
                modifier_name=mod_name,
            )

        elif op == "setup_preview_camera":
            # setup_preview_camera takes target: tuple[float, float, float]
            target_pos = (0.0, 0.0, 0.0)
            loc = params.get("location")
            if isinstance(loc, list):
                loc = tuple(loc)
            dist = params.get("distance", 5.0)
            elev = params.get("elevation_angle", 30.0)
            azim = params.get("azimuth_angle", 45.0)
            cam_name = params.get("camera_name", "PreviewCamera")
            return core.rendering.setup_preview_camera(
                target=target_pos,
                distance=dist,
                elevation_angle=elev,
                azimuth_angle=azim,
                camera_name=cam_name,
            )

        elif op == "setup_studio_lighting":
            target_pos = (0.0, 0.0, 0.0)
            key = params.get("key_energy", 300.0)
            fill = params.get("fill_energy", 100.0)
            rim = params.get("rim_energy", 200.0)
            return core.rendering.setup_studio_lighting(
                target=target_pos,
                key_energy=key,
                fill_energy=fill,
                rim_energy=rim,
            )

        elif op == "render_preview":
            out_path = params.get("output_path") or default_output_path
            res_x = params.get("resolution_x", 1024)
            res_y = params.get("resolution_y", 1024)
            samps = params.get("samples", 64)
            return core.rendering.render_preview(
                output_path=out_path,
                resolution_x=res_x,
                resolution_y=res_y,
                samples=samps,
            )

        elif op == "save_checkpoint":
            path = params.get("checkpoint_path") or ""
            return core.project.save_checkpoint(checkpoint_path=path)

        elif op == "save_project":
            path = params.get("filepath") or ""
            return core.project.save_project(filepath=path)

        elif op == "export_asset":
            out_dir = params.get("output_dir") or ""
            fmt = params.get("format", "FBX")
            return core.project.export_asset(output_dir=out_dir, format=fmt)

        elif op == "restore_checkpoint":
            path = params.get("checkpoint_path") or ""
            return core.project.restore_checkpoint(checkpoint_path=path)

        else:
            raise ValueError(f"Unsupported core operation: {op}")
