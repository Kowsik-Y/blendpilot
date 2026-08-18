"""
BlendPilot — Validation Operators

Bridge handlers for deterministic geometry QA checks.
Wraps core/validation.py.
"""

from __future__ import annotations

import logging
from typing import Any

from blender_addon.operators import register_command

logger = logging.getLogger("blendpilot.addon.operators.validation")


def handle_validate_asset(params: dict[str, Any]) -> dict[str, Any]:
    """Handle validate_asset command."""
    from core.validation import validate_asset

    expected_dimensions = None
    if "expected_dimensions" in params and params["expected_dimensions"]:
        expected_dimensions = tuple(params["expected_dimensions"])

    return validate_asset(
        name=params["name"],
        triangle_limit=params.get("triangle_limit", 10_000),
        expected_dimensions=expected_dimensions,
        dimension_tolerance=params.get("dimension_tolerance", 0.1),
    )


def handle_check_triangle_count(params: dict[str, Any]) -> dict[str, Any]:
    """Handle check_triangle_count command."""
    from core.validation import check_triangle_count

    return check_triangle_count(
        name=params["name"],
        triangle_limit=params.get("triangle_limit", 10_000),
    )


def handle_check_normals(params: dict[str, Any]) -> dict[str, Any]:
    """Handle check_normals command."""
    from core.validation import check_normals

    return check_normals(name=params["name"])


def handle_check_non_manifold(params: dict[str, Any]) -> dict[str, Any]:
    """Handle check_non_manifold command."""
    from core.validation import check_non_manifold

    return check_non_manifold(name=params["name"])


def handle_check_transforms(params: dict[str, Any]) -> dict[str, Any]:
    """Handle check_transforms command."""
    from core.validation import check_transforms

    return check_transforms(name=params["name"])


def register() -> None:
    """Register all validation command handlers."""
    register_command("validate_asset", handle_validate_asset)
    register_command("check_triangle_count", handle_check_triangle_count)
    register_command("check_normals", handle_check_normals)
    register_command("check_non_manifold", handle_check_non_manifold)
    register_command("check_transforms", handle_check_transforms)
    logger.debug("Validation operators registered.")
