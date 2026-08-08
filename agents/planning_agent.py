"""
BlendPilot AI — Step-by-Step Design Planning Agent

Workflow 4: Uses LLM to generate creative, context-aware modeling plans that
leverage the full MCP tool registry. Falls back to enhanced procedural plans.
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

        # Try LLM-powered plan generation
        if self.llm_service and self.llm_service.config.api_key:
            try:
                plan = await self._llm_generate_plan(spec, scene, research)
                if plan and len(plan.steps) > 0:
                    logger.info("LLM generated %d-step plan for %s", len(plan.steps), spec.asset_type)
                    return plan
            except Exception as e:
                logger.warning("LLM planning failed (%s), using procedural plan generator", e)

        # Fallback: enhanced procedural plan generator
        return self._generate_procedural_plan(spec)

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
            )
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

    def _generate_procedural_plan(self, spec: DesignSpec) -> DesignPlan:
        """Generate an enhanced, asset-specific procedural plan."""
        steps: list[PlanStep] = []
        w, d, h = spec.dimensions.width, spec.dimensions.depth, spec.dimensions.height

        main_name = f"{spec.asset_type.capitalize()}_Main"

        # Determine primary primitive type based on asset
        cylindrical_assets = {"barrel", "street_lamp", "piston", "robot_wheel", "pipe_valve", "potion", "pillar"}
        spherical_assets = {"crystal", "rock", "potion"}
        if spec.asset_type in cylindrical_assets:
            primitive = "cylinder"
        elif spec.asset_type in spherical_assets:
            primitive = "ico_sphere"
        elif spec.asset_type in {"sword", "blade"}:
            primitive = "cube"
        else:
            primitive = "cube"

        # Step 1: Primary blockout geometry
        steps.append(PlanStep(
            step_id=1,
            description=f"Create primary blockout {primitive} for {spec.asset_type}",
            tool="create_primitive",
            parameters={
                "primitive_type": primitive,
                "name": main_name,
                "dimensions": [w, d, h],
                "location": [0.0, 0.0, h / 2.0],
            },
            expected_outcome=f"Primary {primitive} '{main_name}' centered on ground plane",
        ))

        # Step 2: Bevel modifier for edge detail
        bevel_width = 0.02 if spec.style in ("sci-fi", "industrial") else 0.03
        steps.append(PlanStep(
            step_id=2,
            description=f"Add Bevel modifier ({bevel_width}m width) for edge highlight",
            tool="add_modifier",
            parameters={
                "object_name": main_name,
                "modifier_type": "BEVEL",
                "modifier_name": "EdgeBevel",
                "properties": {"width": bevel_width, "segments": 2},
            },
            dependencies=[1],
            expected_outcome=f"Bevel modifier with {bevel_width}m width on '{main_name}'",
        ))

        # Step 3: Apply Bevel
        steps.append(PlanStep(
            step_id=3,
            description="Apply bevel modifier into geometry",
            tool="apply_modifier",
            parameters={
                "object_name": main_name,
                "modifier_name": "EdgeBevel",
            },
            dependencies=[2],
            expected_outcome="Bevel baked into mesh geometry",
        ))

        # Step 4-6: Asset-specific detail geometry
        step_id = 4
        accent_objects: list[str] = []

        if spec.asset_type in ("crate", "chest", "container"):
            # Lid accent
            accent_name = f"{spec.asset_type.capitalize()}_Lid"
            steps.append(PlanStep(
                step_id=step_id,
                description=f"Create lid accent for {spec.asset_type}",
                tool="create_primitive",
                parameters={
                    "primitive_type": "cube",
                    "name": accent_name,
                    "dimensions": [w * 1.04, d * 1.04, h * 0.12],
                    "location": [0.0, 0.0, h * 0.94],
                },
                dependencies=[1],
                expected_outcome=f"Lid accent '{accent_name}' positioned at top",
            ))
            accent_objects.append(accent_name)
            step_id += 1

            # Bottom trim
            trim_name = f"{spec.asset_type.capitalize()}_Trim"
            steps.append(PlanStep(
                step_id=step_id,
                description="Create bottom trim reinforcement",
                tool="create_primitive",
                parameters={
                    "primitive_type": "cube",
                    "name": trim_name,
                    "dimensions": [w * 1.06, d * 1.06, h * 0.08],
                    "location": [0.0, 0.0, h * 0.04],
                },
                dependencies=[1],
                expected_outcome=f"Bottom trim '{trim_name}' at base",
            ))
            accent_objects.append(trim_name)
            step_id += 1

        elif spec.asset_type == "notebook":
            # Paper block just below the cover.
            pages_name = "Notebook_Pages"
            steps.append(PlanStep(
                step_id=step_id,
                description="Create visible paper block under the notebook cover",
                tool="create_primitive",
                parameters={
                    "primitive_type": "cube",
                    "name": pages_name,
                    "dimensions": [w * 0.94, d * 0.92, h * 0.42],
                    "location": [w * 0.02, 0.0, h * 0.48],
                },
                dependencies=[1],
                expected_outcome="Off-white paper block visible below cover",
            ))
            accent_objects.append(pages_name)
            step_id += 1

            cover_name = "Notebook_Cover"
            steps.append(PlanStep(
                step_id=step_id,
                description="Create thin top cover plate",
                tool="create_primitive",
                parameters={
                    "primitive_type": "cube",
                    "name": cover_name,
                    "dimensions": [w * 1.04, d * 1.04, h * 0.16],
                    "location": [0.0, 0.0, h * 0.98],
                },
                dependencies=[1],
                expected_outcome="Hard cover plate slightly larger than pages",
            ))
            accent_objects.append(cover_name)
            step_id += 1

            spine_name = "Notebook_Spine"
            steps.append(PlanStep(
                step_id=step_id,
                description="Create vertical binding spine strip",
                tool="create_primitive",
                parameters={
                    "primitive_type": "cube",
                    "name": spine_name,
                    "dimensions": [w * 0.12, d * 1.08, h * 1.2],
                    "location": [-w * 0.48, 0.0, h * 0.62],
                },
                dependencies=[1],
                expected_outcome="Raised spine strip along notebook binding",
            ))
            accent_objects.append(spine_name)
            step_id += 1

            for i, y_frac in enumerate([-0.28, 0.0, 0.28]):
                line_name = f"Notebook_Page_Line_{i + 1}"
                steps.append(PlanStep(
                    step_id=step_id,
                    description=f"Create subtle page line {i + 1}",
                    tool="create_primitive",
                    parameters={
                        "primitive_type": "cube",
                        "name": line_name,
                        "dimensions": [w * 0.62, d * 0.012, h * 0.04],
                        "location": [w * 0.12, d * y_frac, h * 1.08],
                    },
                    dependencies=[1],
                    expected_outcome=f"Subtle cover/page line '{line_name}'",
                ))
                accent_objects.append(line_name)
                step_id += 1

        elif spec.asset_type in ("table", "desk"):
            # Table legs
            leg_positions = [
                [w * 0.4, d * 0.35, h * 0.35],
                [-w * 0.4, d * 0.35, h * 0.35],
                [w * 0.4, -d * 0.35, h * 0.35],
                [-w * 0.4, -d * 0.35, h * 0.35],
            ]
            for i, pos in enumerate(leg_positions):
                leg_name = f"Table_Leg_{i + 1}"
                steps.append(PlanStep(
                    step_id=step_id,
                    description=f"Create table leg {i + 1}",
                    tool="create_primitive",
                    parameters={
                        "primitive_type": "cube",
                        "name": leg_name,
                        "dimensions": [0.06, 0.06, h * 0.92],
                        "location": pos,
                    },
                    dependencies=[1],
                    expected_outcome=f"Leg '{leg_name}' positioned",
                ))
                accent_objects.append(leg_name)
                step_id += 1

        elif spec.asset_type in ("barrel", "drum"):
            # Metal hoops
            for i, z_frac in enumerate([0.15, 0.5, 0.85]):
                hoop_name = f"Barrel_Hoop_{i + 1}"
                steps.append(PlanStep(
                    step_id=step_id,
                    description=f"Create metal hoop ring at {int(z_frac * 100)}% height",
                    tool="create_primitive",
                    parameters={
                        "primitive_type": "torus",
                        "name": hoop_name,
                        "dimensions": [w * 1.02, d * 1.02, 0.03],
                        "location": [0.0, 0.0, h * z_frac],
                    },
                    dependencies=[1],
                    expected_outcome=f"Metal hoop '{hoop_name}' wrapping barrel",
                ))
                accent_objects.append(hoop_name)
                step_id += 1

        elif spec.asset_type == "sword":
            # Blade elongation + guard + hilt
            guard_name = "Sword_Guard"
            steps.append(PlanStep(
                step_id=step_id,
                description="Create crossguard tsuba",
                tool="create_primitive",
                parameters={
                    "primitive_type": "cube",
                    "name": guard_name,
                    "dimensions": [0.20, 0.06, 0.03],
                    "location": [0.0, 0.0, 0.30],
                },
                dependencies=[1],
                expected_outcome="Crossguard element",
            ))
            accent_objects.append(guard_name)
            step_id += 1

            hilt_name = "Sword_Hilt"
            steps.append(PlanStep(
                step_id=step_id,
                description="Create wrapped hilt handle",
                tool="create_primitive",
                parameters={
                    "primitive_type": "cylinder",
                    "name": hilt_name,
                    "dimensions": [0.04, 0.04, 0.25],
                    "location": [0.0, 0.0, 0.15],
                },
                dependencies=[1],
                expected_outcome="Hilt handle cylinder",
            ))
            accent_objects.append(hilt_name)
            step_id += 1

        elif spec.asset_type == "pylon":
            # Energy core
            core_name = "Pylon_Core"
            steps.append(PlanStep(
                step_id=step_id,
                description="Create floating energy core",
                tool="create_primitive",
                parameters={
                    "primitive_type": "ico_sphere",
                    "name": core_name,
                    "dimensions": [0.25, 0.25, 0.25],
                    "location": [0.0, 0.0, h * 0.75],
                },
                dependencies=[1],
                expected_outcome=f"Energy core sphere at top section",
            ))
            accent_objects.append(core_name)
            step_id += 1

            # Base platform
            base_name = "Pylon_Base"
            steps.append(PlanStep(
                step_id=step_id,
                description="Create stepped base platform",
                tool="create_primitive",
                parameters={
                    "primitive_type": "cube",
                    "name": base_name,
                    "dimensions": [w * 1.5, d * 1.5, h * 0.1],
                    "location": [0.0, 0.0, h * 0.05],
                },
                dependencies=[1],
                expected_outcome="Wide base platform",
            ))
            accent_objects.append(base_name)
            step_id += 1

        else:
            # Generic accent
            accent_name = f"{spec.asset_type.capitalize()}_Accent"
            steps.append(PlanStep(
                step_id=step_id,
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
            accent_objects.append(accent_name)
            step_id += 1

        # Final step: Checkpoint save
        all_deps = list(range(1, step_id))
        steps.append(PlanStep(
            step_id=step_id,
            description="Save blockout milestone checkpoint",
            tool="save_checkpoint",
            parameters={
                "filepath": f"output/checkpoints/{spec.asset_type}_blockout.blend",
                "checkpoint_name": "01_blockout_complete",
            },
            dependencies=all_deps,
            expected_outcome="Blockout .blend checkpoint saved",
        ))

        return DesignPlan(
            spec_id=f"plan_{spec.asset_type}",
            steps=steps,
            current_step_index=0,
            status=StepStatus.PENDING,
        )
