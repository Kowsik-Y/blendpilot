"""
BlendPilot AI — Unified Generation Agent

Merges autonomous mesh modeling and material/lighting setup into a single
generation step, matching the target architecture:
    Planning Agent → Generation Agent → Scene State → Geometry Validation

The agent:
1. Executes all plan steps via MCP tools (mesh creation, modifiers, transforms)
2. Applies PBR materials and studio lighting
3. Renders a preview image for the downstream Visual Critic
4. Uses LLM-powered adaptive error recovery for failed steps
"""

from __future__ import annotations

import logging
from typing import Any

from mcp_servers.blender.server import BlenderMCPServer
from schemas.design import DesignSpec
from schemas.plan import DesignPlan, StepStatus
from services.llm import LLMService

logger = logging.getLogger("blendpilot.agents.generation")

# Material palette keyed by material token from DesignSpec
_MATERIAL_PALETTE: dict[str, dict[str, Any]] = {
    "dark_metal": {"base_color": [0.12, 0.13, 0.15, 1.0], "metallic": 0.85, "roughness": 0.35},
    "blue_emissive": {
        "base_color": [0.05, 0.4, 0.95, 1.0],
        "metallic": 0.1,
        "roughness": 0.2,
        "emission_color": [0.0, 0.5, 1.0, 1.0],
        "emission_strength": 5.0,
    },
    "wood_grain": {"base_color": [0.4, 0.25, 0.15, 1.0], "metallic": 0.0, "roughness": 0.7},
    "stone_rough": {"base_color": [0.55, 0.52, 0.48, 1.0], "metallic": 0.0, "roughness": 0.9},
    "rusted_metal": {"base_color": [0.45, 0.2, 0.1, 1.0], "metallic": 0.6, "roughness": 0.85},
    "gold_metal": {"base_color": [0.95, 0.78, 0.2, 1.0], "metallic": 1.0, "roughness": 0.15},
    "glass": {
        "base_color": [0.9, 0.95, 1.0, 0.15],
        "metallic": 0.0,
        "roughness": 0.0,
        "emission_strength": 0.0,
    },
    "lava_emissive": {
        "base_color": [1.0, 0.3, 0.0, 1.0],
        "metallic": 0.0,
        "roughness": 0.9,
        "emission_color": [1.0, 0.2, 0.0, 1.0],
        "emission_strength": 8.0,
    },
    "chrome_mirror": {"base_color": [0.9, 0.9, 0.92, 1.0], "metallic": 1.0, "roughness": 0.05},
    "base_gray_pbr": {"base_color": [0.75, 0.75, 0.78, 1.0], "metallic": 0.2, "roughness": 0.4},
}


class GenerationAgent:
    """Unified agent that executes mesh modeling and material/lighting in a single step.

    Execution order:
        1. Sequentially execute all DesignPlan steps via MCP (geometry).
        2. Apply PBR materials from DesignSpec.materials, assign to objects.
        3. Set up 3-point studio lighting and preview camera.
        4. Render a 1024×1024 preview image for the Visual Critic.
    """

    def __init__(
        self,
        mcp_server: BlenderMCPServer | None = None,
        llm_service: LLMService | None = None,
    ):
        self.mcp_server = mcp_server or BlenderMCPServer()
        self.llm_service = llm_service

    async def execute(
        self,
        spec: DesignSpec,
        plan: DesignPlan,
        output_image_path: str | None = None,
    ) -> dict[str, Any]:
        """Run the full generation pipeline and return results.

        Args:
            spec: The validated DesignSpec from the Intent Agent.
            plan: The step-by-step DesignPlan from the Planning Agent.
            output_image_path: Path to write the preview render to.

        Returns:
            dict with keys: success, created_objects, materials_created,
                            preview_image_path, modeling_logs.
        """
        if output_image_path is None:
            output_image_path = f"output/{spec.asset_type}/preview.png"

        logger.info(
            "GenerationAgent starting for '%s' — %d plan steps",
            spec.asset_type,
            len(plan.steps),
        )

        created_objects: list[str] = []
        materials_created: list[str] = []
        modeling_logs: list[dict[str, Any]] = []

        # ── Phase A: Execute Mesh Modeling Steps ──────────────────────────
        for step in plan.steps:
            logger.info(
                "  Step %d/%d: [%s] %s",
                step.step_id,
                len(plan.steps),
                step.tool,
                step.description,
            )
            step.status = StepStatus.IN_PROGRESS
            plan.current_step_index = step.step_id - 1

            result = await self.mcp_server.call_tool(step.tool, step.parameters)
            success = result.get("success", False)

            if success:
                step.status = StepStatus.COMPLETED
                obj_name = (
                    result.get("object_name")
                    or result.get("new_object")
                    or step.parameters.get("name")
                )
                if obj_name and obj_name not in created_objects and step.tool in (
                    "create_primitive",
                    "duplicate_object",
                ):
                    created_objects.append(obj_name)
            else:
                error_msg = result.get("error", "Unknown error")
                logger.warning("  Step %d failed: %s — attempting LLM recovery", step.step_id, error_msg)

                recovered = await self._attempt_recovery(step, error_msg, created_objects)
                if recovered:
                    step.status = StepStatus.COMPLETED
                    if recovered.get("created_object"):
                        created_objects.append(recovered["created_object"])
                    logger.info("  Step %d recovered via LLM", step.step_id)
                else:
                    step.status = StepStatus.FAILED
                    step.error_message = error_msg

            modeling_logs.append({
                "step_id": step.step_id,
                "tool": step.tool,
                "success": step.status == StepStatus.COMPLETED,
                "response": result,
            })

        all_steps_ok = all(s.status == StepStatus.COMPLETED for s in plan.steps)
        plan.status = StepStatus.COMPLETED if all_steps_ok else StepStatus.FAILED

        # ── Phase B: Apply PBR Materials ──────────────────────────────────
        for i, mat_token in enumerate(spec.materials or ["base_gray_pbr"]):
            palette_entry = _MATERIAL_PALETTE.get(mat_token, _MATERIAL_PALETTE["base_gray_pbr"])
            mat_name = f"Mat_{spec.asset_type}_{mat_token}"
            await self.mcp_server.call_tool("create_material", {"name": mat_name, **palette_entry})
            materials_created.append(mat_name)

            # Assign to object at matching index (or first if not enough objects)
            target_obj = created_objects[i] if i < len(created_objects) else (created_objects[0] if created_objects else None)
            if target_obj:
                await self.mcp_server.call_tool("assign_material", {
                    "object_name": target_obj,
                    "material_name": mat_name,
                })

        # ── Phase C: Studio Lighting ──────────────────────────────────────
        await self.mcp_server.call_tool("setup_studio_lighting", {
            "key_energy": 1200.0,
            "fill_energy": 450.0,
            "rim_energy": 700.0,
        })

        # ── Phase D: Preview Camera ───────────────────────────────────────
        await self.mcp_server.call_tool("setup_preview_camera", {
            "target_object": created_objects[0] if created_objects else None,
            "distance": 3.2,
            "focal_length": 50.0,
        })

        # ── Phase E: Render Preview ───────────────────────────────────────
        await self.mcp_server.call_tool("render_preview", {
            "output_path": output_image_path,
            "resolution_x": 1024,
            "resolution_y": 1024,
            "samples": 64,
        })

        logger.info(
            "GenerationAgent complete — objects: %s | materials: %s | success: %s",
            created_objects,
            materials_created,
            all_steps_ok,
        )

        return {
            "success": all_steps_ok,
            "created_objects": created_objects,
            "materials_created": materials_created,
            "preview_image_path": output_image_path,
            "modeling_logs": modeling_logs,
            "plan": plan,
        }

    async def _attempt_recovery(
        self,
        failed_step: Any,
        error_msg: str,
        created_objects: list[str],
    ) -> dict[str, Any] | None:
        """Use LLM to suggest an alternative tool call when a step fails."""
        if not self.llm_service or not self.llm_service.config.api_key:
            return None

        import json
        import re

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            system_prompt = (
                "You are a Blender 3D modeling expert. A modeling step has failed. "
                "Analyze the error and suggest a single corrected MCP tool call that achieves "
                "the same goal. Respond ONLY with a JSON object: "
                '{"tool": "<tool_name>", "parameters": {<params>}, "reasoning": "<why>"}'
            )
            user_prompt = (
                f"Failed step: {failed_step.description}\n"
                f"Tool: {failed_step.tool}\n"
                f"Parameters: {json.dumps(failed_step.parameters)}\n"
                f"Error: {error_msg}\n"
                f"Existing objects in scene: {created_objects}\n\n"
                "Suggest a corrected tool call to achieve the same goal."
            )

            response = await self.llm_service.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                response_format={"type": "json_object"},
            )
            if not response:
                return None

            clean = re.sub(r"^```json\s*|\s*```$", "", response.strip(), flags=re.MULTILINE)
            recovery = json.loads(clean)

            tool_name = recovery.get("tool", failed_step.tool)
            params = recovery.get("parameters", failed_step.parameters)
            logger.info(
                "LLM recovery: calling %s (reason: %s)",
                tool_name,
                recovery.get("reasoning", ""),
            )

            retry = await self.mcp_server.call_tool(tool_name, params)
            if retry.get("success", False):
                result: dict[str, Any] = {"success": True}
                if "object_name" in retry:
                    result["created_object"] = retry["object_name"]
                elif "name" in params:
                    result["created_object"] = params["name"]
                return result

        except Exception as exc:
            logger.warning("LLM error recovery failed: %s", exc)

        return None
