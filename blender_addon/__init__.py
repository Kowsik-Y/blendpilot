"""
BlendPilot — Blender Add-on

Registers BlendPilot as a Blender add-on and starts/stops
the bridge server for external communication.

Installation:
    1. In Blender: Edit → Preferences → Add-ons → Install
    2. Select the blender_addon/ folder (or zip it first)
    3. Enable "BlendPilot" in the add-on list

The bridge server starts automatically when the add-on is enabled
and stops when it is disabled.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("blendpilot.addon")

bl_info = {
    "name": "BlendPilot",
    "author": "BlendPilot Team",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > BlendPilot",
    "description": "AI-driven 3D asset generation copilot — bridge server for external control",
    "doc_url": "",
    "category": "3D View",
}

# Default bridge configuration
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 9876


def register():
    """Register the add-on and start the bridge server.

    Called by Blender when the add-on is enabled.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s — %(levelname)s — %(message)s",
    )

    logger.info("=" * 50)
    logger.info("BlendPilot — Registering add-on")
    logger.info("=" * 50)

    try:
        from blender_addon.bridge import start_bridge_server

        start_bridge_server(host=BRIDGE_HOST, port=BRIDGE_PORT)
        logger.info("BlendPilot add-on registered successfully.")
        logger.info("Bridge server running on http://%s:%d",
                    BRIDGE_HOST, BRIDGE_PORT)

    except Exception as e:
        logger.error("Failed to start bridge server: %s", e)
        raise


def unregister():
    """Unregister the add-on and stop the bridge server.

    Called by Blender when the add-on is disabled.
    """
    logger.info("BlendPilot — Unregistering add-on")

    try:
        from blender_addon.bridge import stop_bridge_server

        stop_bridge_server()
        logger.info("BlendPilot add-on unregistered.")

    except Exception as e:
        logger.error("Error stopping bridge server: %s", e)
