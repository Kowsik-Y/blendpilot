"""
BlendPilot AI — Blender Runner Script

This script is executed by Blender in background mode to start the bridge server.
Usage: blender --background --python backend/blender_runner.py
"""

import sys
import os
import time
import logging

# Add the project root to sys.path so we can import blender_addon and core
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("blendpilot.blender_runner")

def main():
    logger.info("Starting Blender bridge server inside Blender...")
    
    try:
        # Import the add-on's bridge module directly
        from blender_addon.bridge import start_bridge_server
        
        # Start the server (runs in a daemon thread)
        # We use default host/port. If needed, we could read from env or args.
        start_bridge_server(host="127.0.0.1", port=9876)
        
        logger.info("Bridge server started. Running event loop...")
        
        # Keep the process alive
        while True:
            time.sleep(1.0)
            
    except Exception as e:
        logger.exception(f"Failed to start Blender bridge: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
