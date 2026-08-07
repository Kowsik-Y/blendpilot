"""
BlendPilot AI — Operator Registry

Central registry mapping command names to handler functions.
Each handler validates parameters and delegates to core/ functions.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("blendpilot.addon.operators")

# The registry is populated by each operator module's register() call
COMMAND_REGISTRY: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def register_command(name: str, handler: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    """Register a command handler in the global registry.

    Args:
        name: Command name (must match a CommandName enum value).
        handler: Function that takes a parameters dict and returns a result dict.
    """
    if name in COMMAND_REGISTRY:
        logger.warning("Overwriting existing handler for command '%s'", name)
    COMMAND_REGISTRY[name] = handler
    logger.debug("Registered command handler: %s", name)


def get_handler(name: str) -> Callable[[dict[str, Any]], dict[str, Any]] | None:
    """Look up a command handler by name.

    Args:
        name: Command name.

    Returns:
        The handler function, or None if not registered.
    """
    return COMMAND_REGISTRY.get(name)


def list_commands() -> list[str]:
    """Return a sorted list of all registered command names."""
    return sorted(COMMAND_REGISTRY.keys())


def register_all_operators() -> None:
    """Register all operator modules.

    Called during add-on registration to populate the command registry.
    """
    from blender_addon.operators import (
        objects,
        modeling,
        materials,
        rendering,
        validation,
        export,
    )

    objects.register()
    modeling.register()
    materials.register()
    rendering.register()
    validation.register()
    export.register()

    logger.info("Registered %d command handlers: %s", len(COMMAND_REGISTRY), list_commands())
