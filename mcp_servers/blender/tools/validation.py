"""
BlendPilot AI — Validation MCP Tools

Deterministic geometry QA tools for checking polygon counts, manifold topology, normals, and transforms.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from schemas.validation import QACheckResult, ValidationReport
from services.blender_client import BlenderClient


class ValidateAssetInput(BaseModel):
    """Input parameters for complete deterministic asset validation."""
    object_name: str = Field(..., description="Target object name to validate")
    triangle_limit: int = Field(default=10000, gt=0, description="Max allowed triangle count")
    target_engine: str = Field(default="Unity", description="Target platform (Unity, Unreal, WebGL, Godot)")


class CheckMetricInput(BaseModel):
    """Input parameters for checking a single geometric metric."""
    object_name: str = Field(..., description="Target object name")


class CheckTriangleCountInput(BaseModel):
    """Input parameters for checking triangle budget."""
    object_name: str = Field(..., description="Target object name")
    max_triangles: int = Field(default=8000, gt=0, description="Maximum triangle threshold")


async def validate_asset(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Perform a comprehensive deterministic geometry QA check on a mesh object, returning PASS/FAIL status and any detected issues."""
    validated = ValidateAssetInput.model_validate(params)
    response = await client.validate_asset(
        name=validated.object_name,
        triangle_limit=validated.triangle_limit,
    )
    if not response.success or not response.result:
        return {
            "success": False,
            "passed": False,
            "error": response.error or f"Validation failed for '{validated.object_name}'",
            "result": ValidationReport(
                passed=False,
                checks=[QACheckResult(
                    passed=False,
                    severity="high",
                    check_name="mcp_execution_error",
                    object=validated.object_name,
                    message=response.error or "Unknown error",
                    suggested_action="Check Blender server connection."
                )]
            ).model_dump(),
        }
    return {
        "success": True,
        "passed": response.result.get("passed", False),
        "result": response.result,
    }


async def check_non_manifold(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Check if a mesh has non-manifold geometry, holes, or loose vertices/edges."""
    validated = CheckMetricInput.model_validate(params)
    response = await client.check_non_manifold(name=validated.object_name)
    return {
        "success": response.success,
        "object_name": validated.object_name,
        "is_manifold": response.result.get("is_manifold", False) if response.result else False,
        "issues": response.result.get("non_manifold_elements", 0) if response.result else 0,
        "error": response.error,
    }


async def check_normals(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Check for inverted, flipped, or inconsistent face normals."""
    validated = CheckMetricInput.model_validate(params)
    response = await client.check_normals(name=validated.object_name)
    return {
        "success": response.success,
        "object_name": validated.object_name,
        "consistent_normals": response.result.get("consistent", True) if response.result else True,
        "flipped_faces": response.result.get("flipped_count", 0) if response.result else 0,
        "error": response.error,
    }


async def check_triangle_count(client: BlenderClient, params: dict[str, Any]) -> dict[str, Any]:
    """Verify that the object's triangle count stays within the specified budget."""
    validated = CheckTriangleCountInput.model_validate(params)
    response = await client.check_triangle_count(
        name=validated.object_name,
        max_triangles=validated.max_triangles,
    )
    return {
        "success": response.success,
        "object_name": validated.object_name,
        "triangle_count": response.result.get("triangle_count", 0) if response.result else 0,
        "within_budget": response.result.get("within_budget", True) if response.result else True,
        "error": response.error,
    }
