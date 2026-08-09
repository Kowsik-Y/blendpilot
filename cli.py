"""
BlendPilot AI — Command Line Interface (CLI)

Thin entry-point for the Stage 7 synchronous pipeline.

Usage:
    python cli.py "Create a red wooden table with four legs"
    python cli.py "Create a blue metal box" --output-dir output/custom
    python cli.py "Create a stool" --mock --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import sys

# ─────────────────────────────────────────────────────────────────────────────
# ANSI colour helpers (no external deps)
# ─────────────────────────────────────────────────────────────────────────────
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def print_banner() -> None:
    banner = rf"""
{CYAN}{BOLD}===============================================================
       ____  _                 _ ____  _ _      _      _    ___
      | __ )| | ___ _ __   __| |  _ \(_) | ___ | |_   / \  |_ _|
      |  _ \| |/ _ \ '_ \ / _` | |_) | | |/ _ \| __| / _ \  | |
      | |_) | |  __/ | | | (_| |  __/| | | (_) | |_ / ___ \ | |
      |____/|_|\___|_| |_|\__,_|_|   |_|_|\___/ \__/_/   \_\___|

         Synchronous 3D Modeling Pipeline Runner - Stage 7
==============================================================={RESET}
"""
    print(banner)


def _print_report(report_lines: list[str], success: bool) -> None:
    """Print the pipeline report with ANSI colouring."""
    colour = GREEN if success else RED
    for line in report_lines:
        if "=" * 10 in line:
            print(f"{colour}{BOLD}{line}{RESET}")
        elif line.strip().startswith("[OK]"):
            print(f"  {GREEN}{line.strip()}{RESET}")
        elif line.strip().startswith("[FAIL]"):
            print(f"  {RED}{line.strip()}{RESET}")
        elif line.strip().startswith("[mock]"):
            print(f"  {YELLOW}{line.strip()}{RESET}")
        else:
            print(f"  {line}")


def main() -> None:
    print_banner()

    parser = argparse.ArgumentParser(
        description="BlendPilot AI — Stage 7 Synchronous Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               '  python cli.py "Create a red wooden table with four legs"\n'
               '  python cli.py "Create a blue metal box" --output-dir output/box\n'
               '  python cli.py "Create a stool" --mock\n',
    )
    parser.add_argument(
        "prompt",
        help="Natural language description of the 3D asset to create",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        default=None,
        help="Directory for output files (default: output/<object_type>/)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=False,
        help="Force mock mode — skip real Blender calls (auto-detected when bpy is absent)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose debug logging",
    )
    args = parser.parse_args()

    print(f"\n{YELLOW}{BOLD}> PROMPT:{RESET} {args.prompt}\n")

    # Import here so the banner always prints before any import errors surface
    from pipeline.sync_pipeline import run_sync_pipeline

    try:
        result = asyncio.run(
            run_sync_pipeline(
                prompt=args.prompt,
                output_dir=args.output_dir,
                mock_mode=True if args.mock else None,
                verbose=args.verbose,
            )
        )
    except ValueError as exc:
        print(f"\n{RED}{BOLD}[ERROR]{RESET} {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\n{RED}{BOLD}[FATAL]{RESET} Pipeline failed unexpectedly: {exc}")
        sys.exit(2)

    _print_report(result.report_lines, result.success)

    if not result.success:
        sys.exit(1)


if __name__ == "__main__":
    main()
