"""
BlendPilot AI — Live Blender Bridge Server Launcher

Starts Blender with the BlendPilot bridge add-on running on localhost:9876.
Can run in headless background mode or interactive GUI mode.

Usage:
    python scripts/start_blender_bridge.py [--gui] [--port 9876]
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("blendpilot.bridge.launcher")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def find_blender_binary() -> str:
    """Find Blender executable on the current system."""
    env_path = os.getenv("BLENDER_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    # macOS standard locations
    mac_paths = [
        "/Applications/Blender.app/Contents/MacOS/Blender",
        os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/Blender"),
    ]
    for path in mac_paths:
        if os.path.exists(path):
            return path

    # Windows standard locations
    if sys.platform == "win32":
        import glob
        win_paths = glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe")
        for path in win_paths:
            if os.path.exists(path):
                return path

    # Linux / PATH
    import shutil
    which_blender = shutil.which("blender")
    if which_blender:
        return which_blender

    raise FileNotFoundError(
        "Blender executable not found. Please set BLENDER_PATH environment variable or install Blender."
    )


def start_bridge(
    blender_path: str | None = None,
    gui: bool = False,
    host: str = "127.0.0.1",
    port: int = 9876,
) -> subprocess.Popen:
    """Launch Blender and start the BlendPilot bridge server."""
    bin_path = blender_path or find_blender_binary()
    logger.info("Found Blender executable at: %s", bin_path)

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Python bootstrap script executed inside Blender
    bootstrap_code = f"""
import sys, os
sys.path.insert(0, {repr(project_root)})
from blender_addon.bridge import start_bridge_server
from blender_addon.operators import register_all_operators

register_all_operators()
start_bridge_server(host={repr(host)}, port={port})
print(f"BlendPilot Bridge active on http://{host}:{port}")
"""

    cmd = [bin_path]
    if not gui:
        cmd.append("--background")

    cmd.extend(["--python-expr", bootstrap_code])

    logger.info("Launching Blender command: %s", " ".join(cmd[:3]) + " ...")
    process = subprocess.Popen(cmd, cwd=project_root)
    logger.info("Blender bridge process started (PID: %d)", process.pid)
    return process


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start BlendPilot Blender Bridge")
    parser.add_argument("--gui", action="store_true", help="Launch in interactive GUI mode")
    parser.add_argument("--host", default="127.0.0.1", help="Bridge host")
    parser.add_argument("--port", type=int, default=9876, help="Bridge port")
    args = parser.parse_args()

    proc = start_bridge(gui=args.gui, host=args.host, port=args.port)
    try:
        proc.wait()
    except KeyboardInterrupt:
        logger.info("Terminating Blender bridge...")
        proc.terminate()
        proc.wait()
