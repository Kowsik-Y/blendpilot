"""
BlendPilot AI — Deterministic Geometry QA Engine (Stage 9)

A pure-Python engine that validates a generated asset against its DesignSpec
by inspecting the captured SceneState (no live Blender process required).
"""

from typing import Any
from schemas.design import DesignSpec
from schemas.scene import SceneSummary
from schemas.validation import CheckResult, ValidationReport, Severity

class GeometryQAEngine:
    """Runs deterministic validation checks on a scene snapshot."""

    def __init__(self, scene_state: SceneSummary | dict[str, Any], spec: DesignSpec | dict[str, Any]):
        # Parse inputs gracefully to support both raw dicts and Pydantic models
        if isinstance(scene_state, dict):
            from schemas.scene import SceneSummary
            self.scene = SceneSummary.model_validate(scene_state)
        else:
            self.scene = scene_state

        if isinstance(spec, dict):
            from schemas.design import DesignSpec
            self.spec = DesignSpec.model_validate(spec)
        else:
            self.spec = spec

    def validate(self, created_objects: list[str]) -> ValidationReport:
        """Run all checks and return a structured report."""
        checks = []
        
        # 8. Missing required objects (Check entire scene context)
        checks.append(self._check_missing_required_objects(created_objects))

        for obj_name in created_objects:
            obj = self._get_object(obj_name)
            if not obj:
                continue

            # 1. Empty mesh
            checks.append(self._check_empty_mesh(obj))
            
            # 2. Zero dimensions
            checks.append(self._check_zero_dimensions(obj))
            
            # 3. Invalid scale
            checks.append(self._check_invalid_scale(obj))
            
            # 4. Non-manifold geometry
            checks.append(self._check_non_manifold_geometry(obj))
            
            # 5. Duplicate vertices (Heuristic check if very high vs poly count)
            checks.append(self._check_duplicate_vertices(obj))
            
            # 6. Invalid normals
            checks.append(self._check_invalid_normals(obj))
            
            # 7. Missing materials
            checks.append(self._check_missing_materials(obj))
            
            # 9. Excessive polygon count
            checks.append(self._check_excessive_polygon_count(obj))

        # Overall PASS if there are no HIGH or CRITICAL failures
        has_major_failures = any(
            not c.passed and c.severity in (Severity.HIGH, Severity.CRITICAL) 
            for c in checks
        )

        return ValidationReport(
            passed=not has_major_failures,
            checks=checks
        )

    # --- Internal Checks ---

    def _get_object(self, name: str):
        for obj in self.scene.objects:
            if obj.name == name:
                return obj
        return None

    def _check_empty_mesh(self, obj) -> CheckResult:
        is_empty = obj.mesh_stats is None or obj.mesh_stats.vertex_count == 0 or obj.mesh_stats.face_count == 0
        return CheckResult(
            passed=not is_empty,
            severity=Severity.CRITICAL,
            check_name="empty_mesh",
            object=obj.name,
            message="Mesh has no vertices or faces" if is_empty else "Mesh contains geometry",
            suggested_action="Regenerate object base primitives" if is_empty else None
        )

    def _check_zero_dimensions(self, obj) -> CheckResult:
        dims = obj.dimensions
        is_zero = dims[0] <= 0 or dims[1] <= 0 or dims[2] <= 0
        return CheckResult(
            passed=not is_zero,
            severity=Severity.CRITICAL,
            check_name="zero_dimensions",
            object=obj.name,
            message=f"Dimensions contain zero or negative values: ({dims[0]}, {dims[1]}, {dims[2]})" if is_zero else "Dimensions are valid",
            suggested_action="Scale object to match specification" if is_zero else None
        )

    def _check_invalid_scale(self, obj) -> CheckResult:
        scale = obj.transform.scale
        # Expected applied scale is ~ (1.0, 1.0, 1.0)
        is_invalid = abs(scale[0] - 1.0) > 0.01 or abs(scale[1] - 1.0) > 0.01 or abs(scale[2] - 1.0) > 0.01
        return CheckResult(
            passed=not is_invalid,
            severity=Severity.MEDIUM,
            check_name="invalid_scale",
            object=obj.name,
            message=f"Unapplied scale detected: ({scale[0]:.3f}, {scale[1]:.3f}, {scale[2]:.3f})" if is_invalid else "Scale is applied (1.0, 1.0, 1.0)",
            suggested_action="Apply transform (scale) to the object" if is_invalid else None
        )

    def _check_non_manifold_geometry(self, obj) -> CheckResult:
        # We rely on the scene inspector's non-manifold edge count
        edges = obj.mesh_stats.non_manifold_edges if (obj.mesh_stats and obj.mesh_stats.non_manifold_edges is not None) else 0
        is_non_manifold = edges > 0
        return CheckResult(
            passed=not is_non_manifold,
            severity=Severity.HIGH,
            check_name="non_manifold_geometry",
            object=obj.name,
            message=f"Found {edges} non-manifold edges" if is_non_manifold else "Geometry is manifold",
            suggested_action="Merge by distance and recalculate topology" if is_non_manifold else None
        )

    def _check_duplicate_vertices(self, obj) -> CheckResult:
        # If vertex count is absurdly higher than expected for the face count
        # (e.g. all faces disconnected), it suggests duplicates.
        v_count = obj.mesh_stats.vertex_count if obj.mesh_stats else 0
        f_count = obj.mesh_stats.face_count if obj.mesh_stats else 0
        has_duplicates = False
        if f_count > 0 and v_count > (f_count * 4): # Rule of thumb heuristic
            has_duplicates = True
        return CheckResult(
            passed=not has_duplicates,
            severity=Severity.MEDIUM,
            check_name="duplicate_vertices",
            object=obj.name,
            message="Possible duplicate vertices detected due to high vertex-to-face ratio" if has_duplicates else "Vertex count looks reasonable",
            suggested_action="Merge vertices by distance" if has_duplicates else None
        )

    def _check_invalid_normals(self, obj) -> CheckResult:
        flipped = obj.mesh_stats.flipped_faces if (obj.mesh_stats and obj.mesh_stats.flipped_faces is not None) else 0
        is_invalid = flipped > 0
        return CheckResult(
            passed=not is_invalid,
            severity=Severity.MEDIUM,
            check_name="invalid_normals",
            object=obj.name,
            message=f"Found {flipped} flipped faces" if is_invalid else "Normals appear consistent",
            suggested_action="Recalculate normals outside" if is_invalid else None
        )

    def _check_missing_materials(self, obj) -> CheckResult:
        missing = len(obj.material_slots) == 0
        return CheckResult(
            passed=not missing,
            severity=Severity.LOW,
            check_name="missing_materials",
            object=obj.name,
            message="No material slots assigned" if missing else f"Object has {len(obj.material_slots)} material(s)",
            suggested_action="Create and assign a material based on the design specification" if missing else None
        )

    def _check_excessive_polygon_count(self, obj) -> CheckResult:
        limit = self.spec.triangle_limit
        f_count = obj.mesh_stats.face_count if obj.mesh_stats else 0
        # To be safe, compare face count against triangle limit
        is_excessive = f_count > limit
        return CheckResult(
            passed=not is_excessive,
            severity=Severity.HIGH,
            check_name="excessive_polygon_count",
            object=obj.name,
            message=f"Polygon count ({f_count}) exceeds budget ({limit})" if is_excessive else "Polygon count within budget",
            suggested_action="Apply Decimate modifier" if is_excessive else None
        )

    def _check_missing_required_objects(self, created_objects: list[str]) -> CheckResult:
        found_count = 0
        for name in created_objects:
            if self._get_object(name):
                found_count += 1
                
        is_missing = found_count == 0 and len(created_objects) > 0
        return CheckResult(
            passed=not is_missing,
            severity=Severity.HIGH,
            check_name="missing_required_objects",
            object="Scene",
            message="No newly generated objects found in the scene context" if is_missing else f"Found {found_count} expected objects",
            suggested_action="Verify generation step and object naming" if is_missing else None
        )
