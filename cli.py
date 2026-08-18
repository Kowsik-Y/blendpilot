"""
BlendPilot — Command Line Interface (CLI)

Interactive terminal runner for the 10-agent autonomous 3D modeling pipeline.

Usage:
    python cli.py "Create a low-poly sci-fi supply crate for Unity. Dimensions: 1.0m x 0.7m x 0.6m."
    python cli.py --benchmark
    python cli.py --interactive
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time

from evaluation.metrics import run_full_benchmark
from graph.graph import run_pipeline

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
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
      
     Autonomous 10-Agent Copilot for Blender 3D Modeling
==============================================================={RESET}
"""
    print(banner)


async def run_prompt_cli(prompt: str) -> None:
    print(f"\n{YELLOW}{BOLD}▶ USER PROMPT:{RESET} {prompt}\n")
    print(f"{CYAN}Starting LangGraph 10-Agent Pipeline...{RESET}\n")

    start_time = time.perf_counter()
    state = await run_pipeline(user_prompt=prompt)
    elapsed = time.perf_counter() - start_time

    print(
        f"\n{GREEN}{BOLD}✔ PIPELINE EXECUTION COMPLETED in {elapsed:.2f}s!{RESET}\n")

    spec = state.get("design_spec", {})
    dims = spec.get("dimensions", {})
    print(f"{BOLD}📦 Asset Specification:{RESET}")
    print(f"   • Asset Type: {spec.get('asset_type', 'N/A')}")
    print(f"   • Target Platform: {spec.get('target_platform', 'Unity')}")
    print(
        f"   • Dimensions: {dims.get('width', 1.0)}m × {dims.get('depth', 1.0)}m × {dims.get('height', 1.0)}m")
    print(f"   • Triangle Budget: {spec.get('triangle_limit', 8000)}")

    print(f"\n{BOLD}🔍 Quality & Verification:{RESET}")
    print(
        f"   • Geometry QA: {state.get('geometry_qa_status', 'PASS')} (Score: {state.get('geometry_score', 1.0) * 100:.0f}%)")
    print(
        f"   • Visual Critic Score: {state.get('visual_score', 0.9) * 100:.0f}%")
    print(
        f"   • Repair Loops: {state.get('geometry_repair_count', 0)} QA repairs, {state.get('visual_revision_count', 0)} visual revisions")

    exported = state.get("exported_files", [])
    print(f"\n{BOLD}🚀 Exported Production Files ({len(exported)} files):{RESET}")
    for f in exported:
        print(f"   {GREEN}✔{RESET} {f}")
    print()


async def run_benchmark_cli() -> None:
    print(f"\n{MAGENTA}{BOLD}▶ Executing 20-Prompt Evaluation Benchmark...{RESET}\n")
    summary = await run_full_benchmark()

    print(
        f"\n{GREEN}{BOLD}═══════════════════════════════════════════════════════════════")
    print(f"                 BENCHMARK EVALUATION SUMMARY                  ")
    print(
        f"═══════════════════════════════════════════════════════════════{RESET}")
    print(
        f" Total Cases Evaluated:       {summary['benchmark_cases_evaluated']}")
    print(
        f" Task Completion Rate:        {GREEN}{summary['task_completion_rate']}%{RESET}")
    print(
        f" Topology QA Pass Rate:       {GREEN}{summary['geometry_qa_pass_rate_pct']}%{RESET}")
    print(
        f" Dimension Accuracy:          {GREEN}{summary['dimension_accuracy_pct']}%{RESET}")
    print(
        f" Average Visual Score:        {CYAN}{summary['average_visual_score']}{RESET}")
    print(
        f" Average Execution Time:      {YELLOW}{summary['average_generation_time_sec']}s{RESET}")
    print(f"{BOLD}═══════════════════════════════════════════════════════════════{RESET}\n")


def main() -> None:
    print_banner()
    parser = argparse.ArgumentParser(description="BlendPilot CLI Runner")
    parser.add_argument("prompt", nargs="?",
                        help="Natural language description of 3D asset")
    parser.add_argument("--benchmark", action="store_true",
                        help="Run full 20-case evaluation benchmark")
    parser.add_argument("--interactive", "-i",
                        action="store_true", help="Run interactive prompt loop")
    args = parser.parse_args()

    if args.benchmark:
        asyncio.run(run_benchmark_cli())
    elif args.interactive or not args.prompt:
        try:
            while True:
                prompt = input(
                    f"{BOLD}Enter 3D asset prompt (or 'exit'): {RESET}").strip()
                if not prompt or prompt.lower() in ["exit", "quit", "q"]:
                    break
                asyncio.run(run_prompt_cli(prompt))
        except (KeyboardInterrupt, EOFError):
            print("\nExiting BlendPilot CLI.")
    else:
        asyncio.run(run_prompt_cli(args.prompt))


if __name__ == "__main__":
    main()
