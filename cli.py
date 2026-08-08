"""
BlendPilot AI — Command Line Interface (CLI)

Synchronous modeling pipeline runner for Stage 7.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from typing import Any

from agents.intent_agent import IntentAgent
from agents.planning_agent import PlanningAgent
from agents.generation_agent import GenerationAgent

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner() -> None:
    banner = rf"""
{CYAN}{BOLD}===============================================================
       ____  _                 _ ____  _ _      _      _    ___ 
      | __ )| | ___ _ __   __| |  _ \(_) | ___ | |_   / \  |_ _|
      |  _ \| |/ _ \ '_ \ / _` | |_) | | |/ _ \| __| / _ \  | | 
      | |_) | |  __/ | | | (_| |  __/| | | (_) | |_ / ___ \ | | 
      |____/|_|\___|_| |_|\__,_|_|   |_|_|\___/ \__/_/   \_\___|
      
         Synchronous 3D Modeling Pipeline Runner (Stage 7)
==============================================================={RESET}
"""
    print(banner)


async def run_sync_pipeline(prompt: str) -> dict[str, Any]:
    """Execute the synchronous pipeline end-to-end:
    1. Parse intent
    2. Generate modeling plan
    3. Execute supported operations
    4. Save the Blender scene
    5. Render preview
    6. Produce SceneState
    7. Return pipeline execution report data
    """
    print(f"\n{YELLOW}{BOLD}> USER PROMPT:{RESET} {prompt}\n")
    start_time = time.perf_counter()

    # 1. Parse Intent
    print(f"{CYAN}[1/6] Parsing design intent...{RESET}")
    intent_agent = IntentAgent()
    try:
        intent = await intent_agent.execute(user_prompt=prompt)
    except Exception as e:
        print(f"{RED}Error parsing intent: {e}{RESET}")
        raise

    obj_type = intent.object_type
    print(f"      - Category: {intent.object_type}")
    print(f"      - Style: {intent.style}")
    print(f"      - Color: {intent.color or 'default'}")
    print(f"      - Material: {intent.material or 'default'}")

    # 2. Generate Modeling Plan
    print(f"\n{CYAN}[2/6] Generating modeling plan...{RESET}")
    planning_agent = PlanningAgent()
    plan = await planning_agent.execute(intent=intent)
    print(f"      - Generated {len(plan.steps)} modeling steps.")

    # 3. Execute Supported Operations
    print(f"\n{CYAN}[3/6] Executing modeling operations...{RESET}")
    try:
        import bpy
        mock_mode = False
    except ImportError:
        mock_mode = True
    generation_agent = GenerationAgent(mock_mode=mock_mode)
    gen_result = await generation_agent.execute(spec=intent, plan=plan)
    executed_steps = gen_result.get("step_executions", [])
    success_count = sum(1 for s in executed_steps if s.get("success"))
    print(f"      - Executed {success_count}/{len(plan.steps)} steps successfully.")

    # 4. Save Blender Scene
    blend_path = None
    print(f"\n{CYAN}[4/6] Saving Blender scene...{RESET}")
    try:
        import core.project
        os.makedirs(f"output/{obj_type}", exist_ok=True)
        blend_path = os.path.abspath(f"output/{obj_type}/{obj_type}.blend")
        save_res = core.project.save_project(path=blend_path)
        if save_res.get("success"):
            print(f"      - Saved scene to: {blend_path}")
        else:
            print(f"      - Save failed: {save_res.get('message')}")
    except Exception as e:
        print(f"      - Skip saving (Bpy module not available/mocked): {e}")

    # 5. Render Preview
    preview_path = None
    print(f"\n{CYAN}[5/6] Rendering preview...{RESET}")
    try:
        import core.rendering
        os.makedirs(f"output/{obj_type}", exist_ok=True)
        preview_path = os.path.abspath(f"output/{obj_type}/preview.png")
        render_res = core.rendering.render_preview(
            output_path=preview_path,
            resolution_x=512,
            resolution_y=512,
            samples=16,
        )
        if render_res.get("success"):
            print(f"      - Rendered preview to: {preview_path}")
        else:
            print(f"      - Render failed: {render_res.get('message')}")
    except Exception as e:
        print(f"      - Skip rendering (Bpy module not available/mocked): {e}")

    # 6. Produce SceneState
    scene_state = None
    print(f"\n{CYAN}[6/6] Collecting SceneState...{RESET}")
    try:
        from core.scene_inspector import inspect_scene
        scene_state = inspect_scene()
        print(f"      - Successfully inspected scene.")
    except Exception as e:
        print(f"      - Skip inspection (Bpy module not available/mocked): {e}")

    elapsed = time.perf_counter() - start_time

    # 7. Print Concise Execution Report
    print(f"\n{GREEN}{BOLD}===============================================================")
    print(f"                   PIPELINE EXECUTION REPORT                   ")
    print(f"==============================================================={RESET}")
    print(f" {BOLD}Execution Time:{RESET}  {elapsed:.2f} seconds")
    print(f" {BOLD}Overall Status:{RESET}  {'SUCCESS' if gen_result.get('success') else 'FAILED'}")
    print(f" {BOLD}Asset Details:{RESET}")
    print(f"   - Object Type:   {intent.object_type}")
    print(f"   - Color:         {intent.color}")
    print(f"   - Material:      {intent.material}")
    if intent.dimensions:
        print(f"   - Dimensions:    {intent.dimensions.width}m x {intent.dimensions.depth}m x {intent.dimensions.height}m")
    
    print(f"\n {BOLD}Modeling Steps Executed:{RESET}")
    for idx, step in enumerate(executed_steps, 1):
        status_icon = f"[{GREEN}OK{RESET}]" if step.get("success") else f"[{RED}FAIL{RESET}]"
        print(f"   {status_icon} Step {step.get('step_id')}: {step.get('operation')} ({step.get('target')})")

    if scene_state:
        print(f"\n {BOLD}Blender Scene Snapshot:{RESET}")
        print(f"   - Total Objects: {len(scene_state.objects)}")
        print(f"   - Mesh Objects:  {len(scene_state.mesh_objects)}")
        print(f"   - Total Tris:    {scene_state.total_triangle_count}")
        print(f"   - Camera Set:    {scene_state.has_camera}")
        print(f"   - Lights Found:  {len(scene_state.lighting)}")

    if blend_path:
        print(f"\n {BOLD}Saved Deliverables:{RESET}")
        print(f"   - Blend File:    {blend_path}")
        if preview_path:
            print(f"   - Preview Image: {preview_path}")
    print(f"{GREEN}{BOLD}==============================================================={RESET}\n")

    return {
        "intent": intent,
        "plan": plan,
        "generation": gen_result,
        "scene_state": scene_state,
        "blend_path": blend_path,
        "preview_path": preview_path,
        "success": gen_result.get("success", False),
    }


def main() -> None:
    print_banner()
    parser = argparse.ArgumentParser(description="BlendPilot AI CLI Synchronous Pipeline")
    parser.add_argument("prompt", help="Natural language description of 3D asset")
    args = parser.parse_args()

    asyncio.run(run_sync_pipeline(args.prompt))


if __name__ == "__main__":
    main()
