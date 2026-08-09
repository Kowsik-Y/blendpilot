"""
Tests for the Deterministic Geometry QA Engine (Stage 9).
"""

import pytest
from core.geometry_qa_engine import GeometryQAEngine
from schemas.design import DesignSpec, Dimensions
from schemas.scene import SceneSummary, ObjectInfo, MeshStatistics, TransformInfo, ObjectType, MaterialSlot
from schemas.validation import Severity


@pytest.fixture
def base_spec():
    return DesignSpec(
        asset_type="prop",
        dimensions=Dimensions(width=1.0, depth=1.0, height=1.0),
        triangle_limit=1000
    )

@pytest.fixture
def passing_scene():
    return SceneSummary(
        blend_file="test.blend",
        object_count=1,
        objects=[
            ObjectInfo(
                name="TestCube",
                object_type=ObjectType.MESH,
                transform=TransformInfo(scale=(1.0, 1.0, 1.0)),
                dimensions=(1.0, 1.0, 1.0),
                mesh_stats=MeshStatistics(
                    object_name="TestCube",
                    vertex_count=8,
                    edge_count=12,
                    face_count=6,
                    non_manifold_edges=0,
                    flipped_faces=0
                ),
                material_slots=[MaterialSlot(slot_index=0, material_name="Material.001")]
            )
        ]
    )

def test_passing_scene(passing_scene, base_spec):
    engine = GeometryQAEngine(passing_scene, base_spec)
    report = engine.validate(["TestCube"])
    
    assert report.passed is True
    assert len(report.issues) == 0
    # 8 total checks run on the object + 1 global check
    assert len(report.checks) == 9

def test_missing_required_objects(passing_scene, base_spec):
    # Scene has "TestCube", but we tell validate it created "MissingObject"
    engine = GeometryQAEngine(passing_scene, base_spec)
    report = engine.validate(["MissingObject"])
    
    assert report.passed is False
    assert len(report.issues) == 1
    issue = report.issues[0]
    assert issue.check_name == "missing_required_objects"
    assert issue.severity == Severity.HIGH

def test_empty_mesh(passing_scene, base_spec):
    passing_scene.objects[0].mesh_stats.vertex_count = 0
    passing_scene.objects[0].mesh_stats.face_count = 0
    
    engine = GeometryQAEngine(passing_scene, base_spec)
    report = engine.validate(["TestCube"])
    
    assert report.passed is False
    issues = [i for i in report.issues if i.check_name == "empty_mesh"]
    assert len(issues) == 1
    assert issues[0].severity == Severity.CRITICAL

def test_zero_dimensions(passing_scene, base_spec):
    passing_scene.objects[0].dimensions = (0.0, 1.0, 1.0)
    
    engine = GeometryQAEngine(passing_scene, base_spec)
    report = engine.validate(["TestCube"])
    
    assert report.passed is False
    issues = [i for i in report.issues if i.check_name == "zero_dimensions"]
    assert len(issues) == 1
    assert issues[0].severity == Severity.CRITICAL

def test_invalid_scale(passing_scene, base_spec):
    passing_scene.objects[0].transform.scale = (2.0, 1.0, 1.0)
    
    engine = GeometryQAEngine(passing_scene, base_spec)
    report = engine.validate(["TestCube"])
    
    # invalid_scale is MEDIUM severity, so report.passed is still True (no HIGH/CRITICAL)
    assert report.passed is True
    issues = [i for i in report.issues if i.check_name == "invalid_scale"]
    assert len(issues) == 1
    assert issues[0].severity == Severity.MEDIUM

def test_non_manifold_geometry(passing_scene, base_spec):
    passing_scene.objects[0].mesh_stats.non_manifold_edges = 2
    
    engine = GeometryQAEngine(passing_scene, base_spec)
    report = engine.validate(["TestCube"])
    
    assert report.passed is False
    issues = [i for i in report.issues if i.check_name == "non_manifold_geometry"]
    assert len(issues) == 1
    assert issues[0].severity == Severity.HIGH

def test_duplicate_vertices(passing_scene, base_spec):
    passing_scene.objects[0].mesh_stats.face_count = 10
    passing_scene.objects[0].mesh_stats.vertex_count = 50 # > 10*4 (heuristic)
    
    engine = GeometryQAEngine(passing_scene, base_spec)
    report = engine.validate(["TestCube"])
    
    # duplicate_vertices is MEDIUM severity, so report.passed is still True
    assert report.passed is True
    issues = [i for i in report.issues if i.check_name == "duplicate_vertices"]
    assert len(issues) == 1
    assert issues[0].severity == Severity.MEDIUM

def test_invalid_normals(passing_scene, base_spec):
    passing_scene.objects[0].mesh_stats.flipped_faces = 1
    
    engine = GeometryQAEngine(passing_scene, base_spec)
    report = engine.validate(["TestCube"])
    
    # invalid_normals is MEDIUM severity, so report.passed is still True
    assert report.passed is True
    issues = [i for i in report.issues if i.check_name == "invalid_normals"]
    assert len(issues) == 1
    assert issues[0].severity == Severity.MEDIUM

def test_missing_materials(passing_scene, base_spec):
    passing_scene.objects[0].material_slots = []
    
    engine = GeometryQAEngine(passing_scene, base_spec)
    report = engine.validate(["TestCube"])
    
    # missing_materials is LOW severity, so report.passed is still True
    assert report.passed is True
    issues = [i for i in report.issues if i.check_name == "missing_materials"]
    assert len(issues) == 1
    assert issues[0].severity == Severity.LOW

def test_excessive_polygon_count(passing_scene, base_spec):
    passing_scene.objects[0].mesh_stats.face_count = 1200 # spec limit is 1000
    
    engine = GeometryQAEngine(passing_scene, base_spec)
    report = engine.validate(["TestCube"])
    
    assert report.passed is False
    issues = [i for i in report.issues if i.check_name == "excessive_polygon_count"]
    assert len(issues) == 1
    assert issues[0].severity == Severity.HIGH
