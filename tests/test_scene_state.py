"""
BlendPilot AI — Stage 3: Scene State Tests

Tests for:
  schemas/scene_state.py  — all Pydantic models
  core/scene_inspector.py — deterministic scene inspection function

Contract verified:
  1. Models construct with defaults and validate correctly.
  2. Models are fully JSON-serializable (no unserializable types).
  3. inspect_scene() reads ONLY from mocked bpy data — never invents.
  4. inspect_scene() correctly handles empty scenes, mixed object types,
     cameras, lights, materials, modifiers, parent chains, and hidden objects.
  5. SceneState properties (mesh_objects, has_camera, etc.) are correct.
  6. Continuity is preserved when existing_state is passed to inspect_scene().
"""

from __future__ import annotations

import importlib
import json
from unittest.mock import MagicMock

import pytest

from tests.conftest import MockBlenderObject, MockModifierCollection


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _reload_models():
    import schemas.scene_state as m
    importlib.reload(m)
    return m


def _reload_inspector():
    import core.scene_inspector as m
    importlib.reload(m)
    return m


def _make_light_obj(mock_bpy, name="KeyLight"):
    """Register a LIGHT object with realistic data in the mock."""
    obj = MockBlenderObject(name, obj_type="LIGHT")
    light_data = MagicMock()
    light_data.type = "AREA"
    light_data.energy = 500.0
    light_data.color = (1.0, 1.0, 1.0)
    obj.data = light_data
    mock_bpy._test_register_object(obj)
    return obj


def _make_camera_obj(mock_bpy, name="PreviewCamera"):
    """Register a CAMERA object and set it as the active scene camera."""
    obj = MockBlenderObject(name, obj_type="CAMERA")
    cam_data = MagicMock()
    cam_data.lens = 50.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 1000.0
    cam_data.sensor_width = 36.0
    obj.data = cam_data
    mock_bpy._test_register_object(obj)
    mock_bpy.context.scene.camera = obj
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# 1. Vec3 Model
# ─────────────────────────────────────────────────────────────────────────────

class TestVec3:

    def test_default_is_zero(self):
        m = _reload_models()
        v = m.Vec3()
        assert v.x == 0.0
        assert v.y == 0.0
        assert v.z == 0.0

    def test_from_tuple(self):
        m = _reload_models()
        v = m.Vec3.from_tuple((1.0, 2.0, 3.0))
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0

    def test_as_tuple(self):
        m = _reload_models()
        v = m.Vec3(x=4.0, y=5.0, z=6.0)
        assert v.as_tuple() == (4.0, 5.0, 6.0)

    def test_from_list(self):
        m = _reload_models()
        v = m.Vec3.from_tuple([7.0, 8.0, 9.0])
        assert v.z == 9.0

    def test_json_serializable(self):
        m = _reload_models()
        v = m.Vec3(x=1.0, y=2.0, z=3.0)
        data = v.model_dump()
        json.dumps(data)  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# 2. ObjectState Model
# ─────────────────────────────────────────────────────────────────────────────

class TestObjectState:

    def test_requires_name(self):
        m = _reload_models()
        with pytest.raises(Exception):
            m.ObjectState(name="")

    def test_whitespace_name_raises(self):
        m = _reload_models()
        with pytest.raises(Exception):
            m.ObjectState(name="   ")

    def test_valid_construction(self):
        m = _reload_models()
        obj = m.ObjectState(name="MyCube", type=m.ObjectKind.MESH)
        assert obj.name == "MyCube"
        assert obj.type == m.ObjectKind.MESH

    def test_default_type_is_mesh(self):
        m = _reload_models()
        obj = m.ObjectState(name="Obj")
        assert obj.type == m.ObjectKind.MESH

    def test_default_status_is_active(self):
        m = _reload_models()
        obj = m.ObjectState(name="Obj")
        assert obj.status == m.ObjectStatus.ACTIVE

    def test_id_generated_automatically(self):
        m = _reload_models()
        obj = m.ObjectState(name="Obj")
        assert obj.id is not None
        assert len(obj.id) == 12  # uuid4().hex[:12]

    def test_ids_are_unique(self):
        m = _reload_models()
        a = m.ObjectState(name="A")
        b = m.ObjectState(name="B")
        assert a.id != b.id

    def test_material_none_by_default(self):
        m = _reload_models()
        obj = m.ObjectState(name="Obj")
        assert obj.material is None

    def test_modifiers_empty_by_default(self):
        m = _reload_models()
        obj = m.ObjectState(name="Obj")
        assert obj.modifiers == []

    def test_parent_none_by_default(self):
        m = _reload_models()
        obj = m.ObjectState(name="Obj")
        assert obj.parent is None

    def test_mesh_stats_none_for_camera(self):
        m = _reload_models()
        obj = m.ObjectState(name="Cam", type=m.ObjectKind.CAMERA)
        assert obj.mesh_stats is None

    def test_modifier_state_stored(self):
        m = _reload_models()
        mod = m.ModifierState(name="MyBevel", modifier_type="BEVEL")
        obj = m.ObjectState(name="Obj", modifiers=[mod])
        assert obj.modifiers[0].name == "MyBevel"
        assert obj.modifiers[0].modifier_type == "BEVEL"

    def test_json_serializable(self):
        m = _reload_models()
        obj = m.ObjectState(name="Cube")
        data = obj.model_dump(mode="json")
        json.dumps(data)  # must not raise

    def test_hidden_object_status(self):
        m = _reload_models()
        obj = m.ObjectState(name="HiddenObj", visible=False, status=m.ObjectStatus.HIDDEN)
        assert obj.status == m.ObjectStatus.HIDDEN

    def test_object_kind_from_blender_type(self):
        m = _reload_models()
        assert m.ObjectKind.from_blender_type("MESH") == m.ObjectKind.MESH
        assert m.ObjectKind.from_blender_type("CAMERA") == m.ObjectKind.CAMERA
        assert m.ObjectKind.from_blender_type("LIGHT") == m.ObjectKind.LIGHT
        assert m.ObjectKind.from_blender_type("UNKNOWN_TYPE") == m.ObjectKind.OTHER

    def test_material_slots_stored(self):
        m = _reload_models()
        obj = m.ObjectState(
            name="MatObj",
            material="DarkMetal",
            material_slots=["DarkMetal", None],
        )
        assert obj.material == "DarkMetal"
        assert obj.material_slots == ["DarkMetal", None]


# ─────────────────────────────────────────────────────────────────────────────
# 3. MaterialState Model
# ─────────────────────────────────────────────────────────────────────────────

class TestMaterialState:

    def test_defaults(self):
        m = _reload_models()
        mat = m.MaterialState(name="Default")
        assert mat.metallic == 0.0
        assert mat.roughness == 0.5
        assert mat.emission_strength == 0.0
        assert mat.emission_color is None

    def test_metallic_clamped(self):
        m = _reload_models()
        with pytest.raises(Exception):
            m.MaterialState(name="Bad", metallic=1.5)

    def test_roughness_clamped(self):
        m = _reload_models()
        with pytest.raises(Exception):
            m.MaterialState(name="Bad", roughness=-0.1)

    def test_json_serializable(self):
        m = _reload_models()
        mat = m.MaterialState(
            name="TestMat",
            base_color=(0.2, 0.3, 0.4, 1.0),
            metallic=0.8,
            emission_color=(1.0, 0.5, 0.0, 1.0),
            emission_strength=3.0,
        )
        data = mat.model_dump(mode="json")
        json.dumps(data)  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# 4. SceneState Model
# ─────────────────────────────────────────────────────────────────────────────

class TestSceneState:

    def test_default_construction(self):
        m = _reload_models()
        state = m.SceneState()
        assert state.objects == []
        assert state.materials == []
        assert state.camera is None
        assert state.lighting == []
        assert state.iteration == 0
        assert state.status == m.SceneStatus.EMPTY

    def test_inspected_at_set_automatically(self):
        m = _reload_models()
        state = m.SceneState()
        assert state.inspected_at != ""  # auto-set by model_validator

    def test_scene_id_generated(self):
        m = _reload_models()
        a = m.SceneState()
        b = m.SceneState()
        assert a.scene_id != b.scene_id

    def test_mesh_objects_property(self):
        m = _reload_models()
        obj1 = m.ObjectState(name="Cube", type=m.ObjectKind.MESH)
        obj2 = m.ObjectState(name="Cam", type=m.ObjectKind.CAMERA)
        state = m.SceneState(objects=[obj1, obj2])
        assert len(state.mesh_objects) == 1
        assert state.mesh_objects[0].name == "Cube"

    def test_object_names_property(self):
        m = _reload_models()
        obj1 = m.ObjectState(name="A")
        obj2 = m.ObjectState(name="B")
        state = m.SceneState(objects=[obj1, obj2])
        assert set(state.object_names) == {"A", "B"}

    def test_has_camera_false(self):
        m = _reload_models()
        state = m.SceneState()
        assert state.has_camera is False

    def test_has_camera_true(self):
        m = _reload_models()
        cam = m.CameraState(name="Cam")
        state = m.SceneState(camera=cam)
        assert state.has_camera is True

    def test_has_lighting_false(self):
        m = _reload_models()
        state = m.SceneState()
        assert state.has_lighting is False

    def test_has_lighting_true(self):
        m = _reload_models()
        light = m.LightState(name="KeyLight")
        state = m.SceneState(lighting=[light])
        assert state.has_lighting is True

    def test_total_triangle_count(self):
        m = _reload_models()
        stats = m.MeshStats(triangle_count=500)
        obj = m.ObjectState(name="Obj", mesh_stats=stats)
        state = m.SceneState(objects=[obj])
        assert state.total_triangle_count == 500

    def test_total_triangle_count_multiple_objects(self):
        m = _reload_models()
        obj1 = m.ObjectState(name="A", mesh_stats=m.MeshStats(triangle_count=200))
        obj2 = m.ObjectState(name="B", mesh_stats=m.MeshStats(triangle_count=300))
        state = m.SceneState(objects=[obj1, obj2])
        assert state.total_triangle_count == 500

    def test_get_object_by_name(self):
        m = _reload_models()
        obj = m.ObjectState(name="FindMe")
        state = m.SceneState(objects=[obj])
        found = state.get_object("FindMe")
        assert found is not None
        assert found.name == "FindMe"

    def test_get_object_not_found_returns_none(self):
        m = _reload_models()
        state = m.SceneState()
        assert state.get_object("Ghost") is None

    def test_get_material_by_name(self):
        m = _reload_models()
        mat = m.MaterialState(name="FindMat")
        state = m.SceneState(materials=[mat])
        found = state.get_material("FindMat")
        assert found is not None
        assert found.name == "FindMat"

    def test_add_repair_record(self):
        m = _reload_models()
        state = m.SceneState()
        record = m.RepairRecord(iteration=1, priority_issue="geometry")
        state.add_repair_record(record)
        assert len(state.repair_history) == 1
        assert state.iteration == 1

    def test_fully_json_serializable(self):
        m = _reload_models()
        obj = m.ObjectState(
            name="Cube",
            mesh_stats=m.MeshStats(vertex_count=8, edge_count=12, face_count=6, triangle_count=12),
        )
        mat = m.MaterialState(name="Mat", base_color=(0.8, 0.8, 0.8, 1.0))
        cam = m.CameraState(name="Cam")
        light = m.LightState(name="Light")
        repair = m.RepairRecord(iteration=1, operations=["edit_mesh", "render_preview"])
        state = m.SceneState(
            user_prompt="Make a sci-fi crate",
            objects=[obj],
            materials=[mat],
            camera=cam,
            lighting=[light],
            repair_history=[repair],
            iteration=1,
            status=m.SceneStatus.APPROVED,
        )
        data = state.model_dump(mode="json")
        serialized = json.dumps(data)
        assert len(serialized) > 0
        # Round-trip: can reconstruct from JSON
        restored = m.SceneState.model_validate(json.loads(serialized))
        assert restored.user_prompt == "Make a sci-fi crate"
        assert restored.objects[0].name == "Cube"

    def test_validation_report_pending_by_default(self):
        m = _reload_models()
        state = m.SceneState()
        assert state.validation_report.status == "PENDING"

    def test_repair_history_empty_by_default(self):
        m = _reload_models()
        state = m.SceneState()
        assert state.repair_history == []


# ─────────────────────────────────────────────────────────────────────────────
# 5. inspect_scene() — Core Inspector
# ─────────────────────────────────────────────────────────────────────────────

class TestInspectScene:
    """Tests that inspect_scene() correctly reads from the bpy mock."""

    def test_returns_scene_state(self, mock_bpy):
        mod = _reload_inspector()
        from schemas.scene_state import SceneState
        result = mod.inspect_scene()
        assert isinstance(result, SceneState)

    def test_objects_reflect_actual_bpy_data(self, mock_bpy):
        """Only objects in bpy.data.objects appear in the result."""
        mod = _reload_inspector()
        # The mock starts with DefaultCube
        result = mod.inspect_scene()
        assert any(o.name == "DefaultCube" for o in result.objects)

    def test_no_invented_objects(self, mock_bpy):
        """Objects not in bpy.data.objects must not appear in SceneState."""
        mod = _reload_inspector()
        result = mod.inspect_scene()
        # DefaultCube is the only object in the default mock
        assert len(result.objects) == 1

    def test_added_object_appears_in_state(self, mock_bpy):
        mod = _reload_inspector()
        extra = MockBlenderObject("NewMesh", "MESH")
        mock_bpy._test_register_object(extra)
        result = mod.inspect_scene()
        names = [o.name for o in result.objects]
        assert "NewMesh" in names

    def test_removed_object_absent_from_state(self, mock_bpy):
        mod = _reload_inspector()
        # Remove the DefaultCube
        mock_bpy._test_remove_object("DefaultCube")
        mock_bpy.context.scene.objects = list(mock_bpy._test_objects.values())
        result = mod.inspect_scene()
        assert not any(o.name == "DefaultCube" for o in result.objects)

    def test_mesh_object_has_mesh_stats(self, mock_bpy):
        mod = _reload_inspector()
        result = mod.inspect_scene()
        cube = result.get_object("DefaultCube")
        assert cube is not None
        assert cube.mesh_stats is not None
        assert cube.mesh_stats.vertex_count == 8  # MockMeshData has 8 verts

    def test_camera_type_object_has_no_mesh_stats(self, mock_bpy):
        mod = _reload_inspector()
        _make_camera_obj(mock_bpy, "TestCam")
        result = mod.inspect_scene()
        cam_state = result.get_object("TestCam")
        assert cam_state is not None
        assert cam_state.mesh_stats is None

    def test_active_camera_captured(self, mock_bpy):
        mod = _reload_inspector()
        _make_camera_obj(mock_bpy, "ActiveCam")
        result = mod.inspect_scene()
        assert result.camera is not None
        assert result.camera.name == "ActiveCam"

    def test_no_camera_in_scene_is_none(self, mock_bpy):
        mod = _reload_inspector()
        mock_bpy.context.scene.camera = None
        result = mod.inspect_scene()
        assert result.camera is None

    def test_light_objects_captured_in_lighting(self, mock_bpy):
        mod = _reload_inspector()
        _make_light_obj(mock_bpy, "KeyLight")
        result = mod.inspect_scene()
        assert any(l.name == "KeyLight" for l in result.lighting)

    def test_light_energy_read_correctly(self, mock_bpy):
        mod = _reload_inspector()
        _make_light_obj(mock_bpy, "EnergyLight")
        result = mod.inspect_scene()
        light = next(l for l in result.lighting if l.name == "EnergyLight")
        assert light.energy == 500.0

    def test_user_prompt_passed_through(self, mock_bpy):
        mod = _reload_inspector()
        result = mod.inspect_scene(user_prompt="Make a medieval tavern")
        assert result.user_prompt == "Make a medieval tavern"

    def test_materials_read_from_bpy_data(self, mock_bpy):
        mod = _reload_inspector()
        mock_bpy.data.materials.new("DarkMetal")
        result = mod.inspect_scene()
        assert any(mat.name == "DarkMetal" for mat in result.materials)

    def test_no_invented_materials(self, mock_bpy):
        """Materials not in bpy.data.materials must not appear in SceneState."""
        mod = _reload_inspector()
        result = mod.inspect_scene()
        # Default mock has no materials unless explicitly added
        assert not any(mat.name == "InventedMat" for mat in result.materials)

    def test_object_location_read_from_bpy(self, mock_bpy):
        mod = _reload_inspector()
        cube = mock_bpy._test_objects["DefaultCube"]
        cube.location = type(cube.location)((5.0, 3.0, 1.0))
        # Re-create location as MockVector
        from tests.conftest import MockVector
        cube.location = MockVector((5.0, 3.0, 1.0))
        result = mod.inspect_scene()
        cube_state = result.get_object("DefaultCube")
        assert cube_state is not None
        assert cube_state.location.x == 5.0
        assert cube_state.location.y == 3.0
        assert cube_state.location.z == 1.0

    def test_object_type_read_from_bpy(self, mock_bpy):
        mod = _reload_inspector()
        cam = MockBlenderObject("TypeCam", "CAMERA")
        mock_bpy._test_register_object(cam)
        result = mod.inspect_scene()
        cam_state = result.get_object("TypeCam")
        from schemas.scene_state import ObjectKind
        assert cam_state.type == ObjectKind.CAMERA

    def test_hidden_object_status_is_hidden(self, mock_bpy):
        mod = _reload_inspector()
        hidden_obj = MockBlenderObject("HiddenMesh", "MESH")
        hidden_obj._visible = False
        mock_bpy._test_register_object(hidden_obj)
        result = mod.inspect_scene()
        hidden_state = result.get_object("HiddenMesh")
        assert hidden_state is not None
        from schemas.scene_state import ObjectStatus
        assert hidden_state.status == ObjectStatus.HIDDEN

    def test_modifier_on_object_captured(self, mock_bpy):
        mod = _reload_inspector()
        mesh_obj = MockBlenderObject("ModdedMesh", "MESH")
        mesh_obj.modifiers.new("BevelMod", "BEVEL")
        mock_bpy._test_register_object(mesh_obj)
        result = mod.inspect_scene()
        state = result.get_object("ModdedMesh")
        assert state is not None
        assert len(state.modifiers) == 1
        assert state.modifiers[0].name == "BevelMod"
        assert state.modifiers[0].modifier_type == "BEVEL"

    def test_parent_name_captured(self, mock_bpy):
        mod = _reload_inspector()
        parent_obj = MockBlenderObject("ParentMesh", "MESH")
        child_obj = MockBlenderObject("ChildMesh", "MESH")
        child_obj.parent = parent_obj
        mock_bpy._test_register_object(parent_obj)
        mock_bpy._test_register_object(child_obj)
        result = mod.inspect_scene()
        child_state = result.get_object("ChildMesh")
        assert child_state is not None
        assert child_state.parent == "ParentMesh"

    def test_continuity_scene_id_preserved(self, mock_bpy):
        """When existing_state is provided, scene_id is preserved."""
        mod = _reload_inspector()
        from schemas.scene_state import SceneState
        original = mod.inspect_scene()
        original_id = original.scene_id
        updated = mod.inspect_scene(existing_state=original)
        assert updated.scene_id == original_id

    def test_continuity_repair_history_preserved(self, mock_bpy):
        """Repair history carries forward when existing_state is provided."""
        mod = _reload_inspector()
        from schemas.scene_state import RepairRecord
        original = mod.inspect_scene()
        record = RepairRecord(iteration=1, priority_issue="geometry", operations=["recalc_normals"])
        original.add_repair_record(record)
        updated = mod.inspect_scene(existing_state=original)
        assert len(updated.repair_history) == 1
        assert updated.repair_history[0].priority_issue == "geometry"

    def test_inspected_at_is_iso_timestamp(self, mock_bpy):
        mod = _reload_inspector()
        result = mod.inspect_scene()
        from datetime import datetime
        # Should parse without error as an ISO datetime
        dt = datetime.fromisoformat(result.inspected_at)
        assert dt is not None

    def test_result_is_fully_json_serializable(self, mock_bpy):
        """The entire SceneState from inspect_scene() must serialize to JSON."""
        mod = _reload_inspector()
        _make_camera_obj(mock_bpy, "SerializeCam")
        _make_light_obj(mock_bpy, "SerializeLight")
        mock_bpy.data.materials.new("SerializeMat")
        result = mod.inspect_scene(user_prompt="Serialize test")
        data = result.model_dump(mode="json")
        serialized = json.dumps(data)
        assert len(serialized) > 0
        # Round-trip
        restored = result.model_validate(json.loads(serialized))
        assert restored.scene_id == result.scene_id

    def test_status_set_to_empty_when_no_meshes(self, mock_bpy):
        """If there are no MESH objects and status=GENERATED, it becomes EMPTY."""
        mod = _reload_inspector()
        from schemas.scene_state import SceneStatus
        # Remove the DefaultCube so no meshes exist
        mock_bpy._test_remove_object("DefaultCube")
        mock_bpy.context.scene.objects = []
        result = mod.inspect_scene(status=SceneStatus.GENERATED)
        assert result.status == SceneStatus.EMPTY

    def test_mesh_stats_edge_count(self, mock_bpy):
        mod = _reload_inspector()
        result = mod.inspect_scene()
        cube = result.get_object("DefaultCube")
        assert cube.mesh_stats.edge_count == 12  # MockMeshData has 12 edges

    def test_mesh_stats_face_count(self, mock_bpy):
        mod = _reload_inspector()
        result = mod.inspect_scene()
        cube = result.get_object("DefaultCube")
        assert cube.mesh_stats.face_count == 6  # MockMeshData has 6 polygons

    def test_render_engine_read_from_scene(self, mock_bpy):
        mod = _reload_inspector()
        mock_bpy.context.scene.render.engine = "CYCLES"
        result = mod.inspect_scene()
        assert result.render_engine == "CYCLES"

    def test_blend_file_read_from_bpy_data(self, mock_bpy):
        mod = _reload_inspector()
        mock_bpy.data.filepath = "/home/user/project.blend"
        result = mod.inspect_scene()
        assert result.blend_file == "/home/user/project.blend"
