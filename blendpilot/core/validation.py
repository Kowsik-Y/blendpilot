"""
BlendPilot AI — Deterministic Geometry Validation

Implements geometry QA checks that do NOT depend on an LLM.
Uses Blender Python (bpy/bmesh) for deterministic validation.

Matches Workflow 7 (Geometry QA) from the plan.

Runs inside Blender's Python environment.
"""

from __future__ import annotations

import logging
from typing import Any

import bmesh  # type: ignore[import-not-found]
import bpy  # type: ignore[import-not-found]

logger = logging.getLogger("blendpilot.core.validation")


def check_triangle_count(
    name: str,
    triangle_limit: int = 10_000,
) -> dict[str, Any]:
    """Check if an object's triangle count is within budget.

    Args:
        name: Name of the mesh object.
        triangle_limit: Maximum allowed triangle count.

    Returns:
        Dict with 'passed', 'triangle_count', 'triangle_limit', and 'message'.
    """
    _validate_mesh_object(name)
    obj = bpy.data.objects[name]

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    tri_count = sum(len(f.verts) - 2 for f in bm.faces)
    bm.free()

    passed = tri_count <= triangle_limit
    logger.info(
        "Triangle check '%s': %d / %d — %s",
        name, tri_count, triangle_limit, "PASS" if passed else "FAIL",
    )
    return {
        "passed": passed,
        "triangle_count": tri_count,
        "triangle_limit": triangle_limit,
        "message": (
            f"Triangle count {tri_count} is within limit {triangle_limit}."
            if passed
            else f"Triangle count {tri_count} EXCEEDS limit {triangle_limit}."
        ),
    }


def check_normals(name: str) -> dict[str, Any]:
    """Check for flipped normals on a mesh object.

    Args:
        name: Name of the mesh object.

    Returns:
        Dict with 'passed', 'flipped_count', and details.
    """
    _validate_mesh_object(name)
    obj = bpy.data.objects[name]

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    # Check for inconsistent normals by looking at face winding
    # A more practical check: look for faces with normals pointing inward
    flipped_faces = []
    for face in bm.faces:
        # Calculate the centroid of the face
        centroid = face.calc_center_median()
        # If normal points away from origin (roughly), it's probably correct
        # This is a heuristic — proper check would compare adjacent face normals
        dot = centroid.dot(face.normal)
        if dot < 0 and centroid.length > 0.001:
            flipped_faces.append(face.index)

    bm.free()

    passed = len(flipped_faces) == 0
    logger.info(
        "Normal check '%s': %d potentially flipped faces — %s",
        name, len(flipped_faces), "PASS" if passed else "FAIL",
    )
    return {
        "passed": passed,
        "flipped_count": len(flipped_faces),
        "flipped_face_indices": flipped_faces[:20],  # Cap at 20 for readability
        "message": (
            f"All normals appear consistent on '{name}'."
            if passed
            else f"Found {len(flipped_faces)} potentially flipped faces on '{name}'."
        ),
    }


def check_non_manifold(name: str) -> dict[str, Any]:
    """Check for non-manifold geometry (edges shared by != 2 faces).

    Args:
        name: Name of the mesh object.

    Returns:
        Dict with 'passed', 'non_manifold_edge_count', and details.
    """
    _validate_mesh_object(name)
    obj = bpy.data.objects[name]

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.edges.ensure_lookup_table()

    non_manifold_edges = [e.index for e in bm.edges if not e.is_manifold]
    non_manifold_verts = [v.index for v in bm.verts if not v.is_manifold]

    bm.free()

    passed = len(non_manifold_edges) == 0
    logger.info(
        "Non-manifold check '%s': %d edges, %d verts — %s",
        name, len(non_manifold_edges), len(non_manifold_verts),
        "PASS" if passed else "FAIL",
    )
    return {
        "passed": passed,
        "non_manifold_edge_count": len(non_manifold_edges),
        "non_manifold_vertex_count": len(non_manifold_verts),
        "non_manifold_edges": non_manifold_edges[:20],
        "message": (
            f"No non-manifold geometry found on '{name}'."
            if passed
            else (
                f"Found {len(non_manifold_edges)} non-manifold edges "
                f"and {len(non_manifold_verts)} non-manifold verts on '{name}'."
            )
        ),
    }


def check_transforms(name: str) -> dict[str, Any]:
    """Check for unapplied transforms (non-identity scale/rotation).

    Args:
        name: Name of the object.

    Returns:
        Dict with 'passed' and details about unapplied transforms.
    """
    if not name or not name.strip():
        raise ValueError("Object name cannot be empty.")

    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object '{name}' not found in scene.")

    issues = []

    # Check scale
    scale = tuple(round(s, 4) for s in obj.scale)
    if scale != (1.0, 1.0, 1.0):
        issues.append({
            "type": "UNAPPLIED_SCALE",
            "current": scale,
            "expected": (1.0, 1.0, 1.0),
        })

    # Check rotation
    rotation = tuple(round(r, 4) for r in obj.rotation_euler)
    if rotation != (0.0, 0.0, 0.0):
        issues.append({
            "type": "UNAPPLIED_ROTATION",
            "current": rotation,
            "expected": (0.0, 0.0, 0.0),
        })

    passed = len(issues) == 0
    logger.info(
        "Transform check '%s': %d issues — %s",
        name, len(issues), "PASS" if passed else "FAIL",
    )
    return {
        "passed": passed,
        "issues": issues,
        "message": (
            f"Transforms are applied on '{name}'."
            if passed
            else f"Found {len(issues)} unapplied transform(s) on '{name}'."
        ),
    }


def validate_asset(
    name: str,
    triangle_limit: int = 10_000,
    expected_dimensions: tuple[float, float, float] | None = None,
    dimension_tolerance: float = 0.1,
) -> dict[str, Any]:
    """Run a full deterministic validation pass on an asset.

    Combines all individual checks into a single comprehensive result
    matching the ValidationResult schema.

    Args:
        name: Name of the mesh object to validate.
        triangle_limit: Maximum triangle budget.
        expected_dimensions: Expected (width, depth, height), or None to skip.
        dimension_tolerance: Allowed deviation from expected dimensions (meters).

    Returns:
        Dict matching the ValidationResult schema structure.
    """
    _validate_mesh_object(name)

    issues = []
    obj = bpy.data.objects[name]

    # --- Triangle count ---
    tri_result = check_triangle_count(name, triangle_limit)
    if not tri_result["passed"]:
        issues.append({
            "issue_type": "TRIANGLE_OVER_BUDGET",
            "object_name": name,
            "severity": "high",
            "message": tri_result["message"],
            "auto_fixable": True,
        })

    # --- Normals ---
    normal_result = check_normals(name)
    if not normal_result["passed"]:
        issues.append({
            "issue_type": "FLIPPED_NORMALS",
            "object_name": name,
            "severity": "medium",
            "message": normal_result["message"],
            "auto_fixable": True,
        })

    # --- Non-manifold ---
    manifold_result = check_non_manifold(name)
    if not manifold_result["passed"]:
        issues.append({
            "issue_type": "NON_MANIFOLD",
            "object_name": name,
            "severity": "medium",
            "message": manifold_result["message"],
            "auto_fixable": False,
        })

    # --- Transforms ---
    transform_result = check_transforms(name)
    if not transform_result["passed"]:
        for issue in transform_result["issues"]:
            issues.append({
                "issue_type": "UNAPPLIED_TRANSFORM",
                "object_name": name,
                "severity": "medium",
                "message": f"{issue['type']}: current={issue['current']}",
                "auto_fixable": True,
            })

    # --- Materials ---
    if not obj.material_slots or all(
        slot.material is None for slot in obj.material_slots
    ):
        issues.append({
            "issue_type": "MISSING_MATERIAL",
            "object_name": name,
            "severity": "low",
            "message": f"Object '{name}' has no materials assigned.",
            "auto_fixable": False,
        })

    # --- Dimensions ---
    if expected_dimensions is not None:
        actual_dims = tuple(obj.dimensions)
        for axis, (actual, expected) in enumerate(
            zip(actual_dims, expected_dimensions)
        ):
            axis_name = ["width (X)", "depth (Y)", "height (Z)"][axis]
            if abs(actual - expected) > dimension_tolerance:
                issues.append({
                    "issue_type": "DIMENSION_MISMATCH",
                    "object_name": name,
                    "severity": "medium",
                    "message": (
                        f"{axis_name}: actual={actual:.3f}m, "
                        f"expected={expected:.3f}m (tolerance={dimension_tolerance}m)"
                    ),
                    "auto_fixable": True,
                })

    # --- Build result ---
    status = "PASS" if len(issues) == 0 else "FAIL"

    # Count by severity
    severity_counts: dict[str, int] = {}
    for issue in issues:
        sev = issue["severity"]
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    result = {
        "status": status,
        "object_name": name,
        "triangle_count": tri_result["triangle_count"],
        "triangle_limit": triangle_limit,
        "vertex_count": len(obj.data.vertices),
        "face_count": len(obj.data.polygons),
        "dimensions": tuple(obj.dimensions),
        "issues": issues,
        "issues_by_severity": severity_counts,
    }

    logger.info(
        "Validation '%s': %s (%d issues: %s)",
        name, status, len(issues), severity_counts,
    )
    return result


def _validate_mesh_object(name: str) -> None:
    """Helper: validate that name refers to an existing mesh object.

    Raises:
        ValueError: If name is empty, object not found, or not a mesh.
    """
    if not name or not name.strip():
        raise ValueError("Object name cannot be empty.")

    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object '{name}' not found in scene.")

    if obj.type != "MESH":
        raise ValueError(
            f"Object '{name}' is type '{obj.type}', not MESH. "
            "Validation is only available for mesh objects."
        )
