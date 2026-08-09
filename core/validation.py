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


def check_empty_mesh(name: str) -> dict[str, Any]:
    _validate_mesh_object(name)
    obj = bpy.data.objects[name]
    vertex_count = len(obj.data.vertices)
    face_count = len(obj.data.polygons)
    passed = vertex_count > 0 and face_count > 0
    return {
        "passed": passed,
        "vertex_count": vertex_count,
        "face_count": face_count,
        "message": f"Mesh has {vertex_count} vertices and {face_count} faces." if passed else f"Mesh '{name}' is empty (0 vertices or faces).",
    }


def check_zero_dimensions(name: str) -> dict[str, Any]:
    _validate_mesh_object(name)
    obj = bpy.data.objects[name]
    dims = obj.dimensions
    passed = all(d >= 0.001 for d in dims)
    return {
        "passed": passed,
        "dimensions": tuple(dims),
        "message": "Dimensions are valid." if passed else f"Mesh '{name}' has zero or near-zero dimensions: {tuple(dims)}.",
    }


def check_duplicate_vertices(name: str) -> dict[str, Any]:
    _validate_mesh_object(name)
    obj = bpy.data.objects[name]

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    original_count = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    new_count = len(bm.verts)
    bm.free()

    duplicates = original_count - new_count
    passed = duplicates == 0
    return {
        "passed": passed,
        "duplicates": duplicates,
        "message": "No duplicate vertices found." if passed else f"Found {duplicates} duplicate vertices on '{name}'.",
    }


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
    matching the ValidationReport schema.
    """
    _validate_mesh_object(name)

    checks = []
    obj = bpy.data.objects[name]

    # --- Empty Mesh ---
    empty_res = check_empty_mesh(name)
    checks.append({
        "passed": empty_res["passed"],
        "severity": "critical",
        "check_name": "empty_mesh",
        "object": name,
        "message": empty_res["message"],
        "suggested_action": "Check generator logic. Mesh was created without vertices.",
    })

    # --- Zero Dimensions ---
    zero_res = check_zero_dimensions(name)
    checks.append({
        "passed": zero_res["passed"],
        "severity": "critical",
        "check_name": "zero_dimensions",
        "object": name,
        "message": zero_res["message"],
        "suggested_action": "Scale up object or rebuild with valid dimensions.",
    })

    # --- Triangle count ---
    tri_res = check_triangle_count(name, triangle_limit)
    checks.append({
        "passed": tri_res["passed"],
        "severity": "high",
        "check_name": "excessive_polygon_count",
        "object": name,
        "message": tri_res["message"],
        "suggested_action": "Apply a Decimate modifier to reduce polygon count.",
    })

    # --- Duplicate Vertices ---
    dup_res = check_duplicate_vertices(name)
    checks.append({
        "passed": dup_res["passed"],
        "severity": "medium",
        "check_name": "duplicate_vertices",
        "object": name,
        "message": dup_res["message"],
        "suggested_action": "Run remove doubles/merge by distance operation.",
    })

    # --- Normals ---
    normal_res = check_normals(name)
    checks.append({
        "passed": normal_res["passed"],
        "severity": "medium",
        "check_name": "invalid_normals",
        "object": name,
        "message": normal_res["message"],
        "suggested_action": "Recalculate outside normals.",
    })

    # --- Non-manifold ---
    manifold_res = check_non_manifold(name)
    checks.append({
        "passed": manifold_res["passed"],
        "severity": "high",
        "check_name": "non_manifold_geometry",
        "object": name,
        "message": manifold_res["message"],
        "suggested_action": "Manually repair topology or remove loose geometry.",
    })

    # --- Transforms (Invalid Scale) ---
    transform_res = check_transforms(name)
    checks.append({
        "passed": transform_res["passed"],
        "severity": "medium",
        "check_name": "invalid_scale",
        "object": name,
        "message": transform_res["message"],
        "suggested_action": "Apply transforms.",
    })

    # --- Missing Materials ---
    has_mats = bool(obj.material_slots and not all(slot.material is None for slot in obj.material_slots))
    checks.append({
        "passed": has_mats,
        "severity": "low",
        "check_name": "missing_materials",
        "object": name,
        "message": "Materials are assigned." if has_mats else f"Object '{name}' has no materials assigned.",
        "suggested_action": "Assign a material to the object.",
    })

    all_passed = all(c["passed"] for c in checks)

    result = {
        "passed": all_passed,
        "checks": checks,
    }

    logger.info("Validation '%s': %s (%d checks)", name, "PASS" if all_passed else "FAIL", len(checks))
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
