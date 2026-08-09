"""
BlendPilot AI — STAGE 17 Evaluation Benchmark Script

Runs a dataset of 20 modeling prompts through both baseline mode (no self-correction)
and self-correcting mode (BlendPilot default) to quantitatively evaluate the impact
of autonomous repair on generation reliability.
"""

import asyncio
import csv
import json
import logging
import time
import uuid
from typing import Any

from graph.graph import build_blendpilot_graph
from graph.persistence import get_checkpointer
from graph.state import create_initial_state

# Configure logging to just show minimal output during tests
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("blendpilot.benchmark")

BENCHMARK_PROMPTS = [
    "Create a simple red cube",
    "Create a tall wooden cylinder",
    "Create a small green sphere",
    "Create a glass torus",
    "Create a metallic cone",
    "Create a low-poly tree using a cylinder and a cone",
    "Create a blue table with 4 legs",
    "Create a chair with a backrest",
    "Create a floating island with grass on top",
    "Create a coffee mug with a handle",
    "Create a sword with a long blade and a crossguard",
    "Create a spaceship with two wings",
    "Create a stylized house with a slanted roof",
    "Create a shiny golden crown",
    "Create an abstract sculpture using multiple spheres",
    "Create a monitor on a stand",
    "Create a smooth pebble",
    "Create a ruined pillar with cracks",
    "Create a bookshelf with 3 shelves",
    "Create a simple bed with a pillow",
]


async def run_prompt(prompt: str, baseline_mode: bool) -> dict[str, Any]:
    """Execute a single prompt and return its metrics."""
    logger.info(f"--- Running Prompt (Baseline={baseline_mode}): {prompt} ---")
    session_id = str(uuid.uuid4())
    checkpointer = get_checkpointer()
    graph = build_blendpilot_graph(checkpointer=checkpointer)

    initial_state = create_initial_state(
        user_prompt=prompt,
        session_id=session_id,
        baseline_mode=baseline_mode,
        overrides={"mock_mode": True}  # Use mock mode to run in CI/headless without Blender
    )
    
    config = {"configurable": {"thread_id": session_id}}
    
    start_time = time.time()
    try:
        final_state = await graph.ainvoke(initial_state, config=config)
    except Exception as e:
        logger.error(f"Graph execution crashed: {e}")
        final_state = {"status": "FAILED", "error": str(e)}
        
    execution_time = time.time() - start_time

    val_report = final_state.get("validation_report") or {}
    vis_report = final_state.get("vision_report") or {}

    metrics = {
        "prompt": prompt,
        "mode": "baseline" if baseline_mode else "self-correcting",
        "generation_success": final_state.get("status") in ("COMPLETED", "REVIEW_REQUIRED"),
        "geometry_pass": val_report.get("passed", False),
        "vision_pass": vis_report.get("overall_result") == "PASS",
        "human_intervention": final_state.get("status") == "REVIEW_REQUIRED",
        "iterations": final_state.get("iteration_count", 0),
        "execution_time_sec": round(execution_time, 2),
    }
    
    # In self-correcting mode, if it passed after iterating, it was a successful repair
    metrics["repair_success"] = False
    if not baseline_mode and metrics["geometry_pass"] and metrics["vision_pass"] and metrics["iterations"] > 0:
        metrics["repair_success"] = True

    return metrics


async def run_benchmark(output_json: str = "benchmark_results.json", output_csv: str = "benchmark_results.csv", limit: int | None = None):
    """Run the benchmark suite."""
    prompts = BENCHMARK_PROMPTS[:limit] if limit else BENCHMARK_PROMPTS
    results = []

    for prompt in prompts:
        # Run baseline
        baseline_metrics = await run_prompt(prompt, baseline_mode=True)
        results.append(baseline_metrics)
        
        # Run self-correcting
        sc_metrics = await run_prompt(prompt, baseline_mode=False)
        results.append(sc_metrics)
        
    # Aggregate stats
    baseline_results = [r for r in results if r["mode"] == "baseline"]
    sc_results = [r for r in results if r["mode"] == "self-correcting"]
    
    def calc_stats(run_results):
        count = len(run_results)
        if count == 0:
            return {}
        return {
            "generation_success_rate": sum(1 for r in run_results if r["generation_success"]) / count,
            "geometry_pass_rate": sum(1 for r in run_results if r["geometry_pass"]) / count,
            "vision_pass_rate": sum(1 for r in run_results if r["vision_pass"]) / count,
            "human_intervention_rate": sum(1 for r in run_results if r["human_intervention"]) / count,
            "avg_iterations": sum(r["iterations"] for r in run_results) / count,
            "avg_execution_time": sum(r["execution_time_sec"] for r in run_results) / count,
            "repair_success_rate": sum(1 for r in run_results if r.get("repair_success", False)) / count,
        }

    summary = {
        "baseline": calc_stats(baseline_results),
        "self_correcting": calc_stats(sc_results),
    }
    
    final_output = {
        "summary": summary,
        "runs": results
    }

    # Write JSON
    with open(output_json, "w") as f:
        json.dump(final_output, f, indent=4)
        
    # Write CSV
    if results:
        keys = results[0].keys()
        with open(output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
            
    logger.info(f"Benchmark completed. Results saved to {output_json} and {output_csv}.")
    logger.info(f"Summary: {json.dumps(summary, indent=4)}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
