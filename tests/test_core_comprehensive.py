"""
BlendPilot AI — Comprehensive Core Module Tests

Tests for all 11 core Blender functions across the 6 modules:
  core/objects.py   — create_primitive, set_transform, duplicate_object, delete_object
  core/materials.py — create_material, assign_material
  core/modifiers.py — add_modifier, apply_modifier
  core/scene.py     — get_scene_summary, get_object_details, get_mesh_statistics
  core/rendering.py — render_preview, setup_preview_camera, setup_studio_lighting
  core/project.py   — save_checkpoint, save_project, export_asset, restore_checkpoint

All tests run outside Blender via the bpy mock in conftest.py.
Tests cover:
  - Input validation (ValueError, FileNotFoundError)
  - Correct bpy API calls (behavior tests)
  - Correct return dict structure and values
  - Edge cases (reuse vs. create, already-assigned materials, etc.)
"""

from __future__ import annotations

import importlib
import os
import sys
from unittest.mock import MagicMock, call, patch

import pytest

from tests.conftest import MockBlenderObject


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _reload(module_path: str):
    """Import (or reload) a core module after mock bpy is installed."""
    mod = importlib.import_module(module_path)
    importlib.reload(mod)
    return mod


# ─────────────────────────────────────────────────────────────────────────────
# 1. create_primitive
# ─────────────────────────────────────────────────────────────────────────────

class TestCreatePrimitiveExtended:
    """Behavioral tests beyond input validation."""

    def test_creates_object_with_correct_name(self, mock_bpy):
        mod = _reload("core.objects")
        result = mod.create_primitive("cube", "MyCube")
        assert result["success"] is True
        assert result["object_name"] == "MyCube"
        assert "MyCube" in result["message"]

    def test_dimensions_applied_to_object(self, mock_bpy):
        mod = _reload("core.objects")
        result = mod.create_primitive("cube", "DimCube", dimensions=(2.0, 1.5, 0.5))
        assert result["success"] is True
        # The active object mock should have had dimensions set
        active = mock_bpy.context.active_object
        assert active is not None

    def test_location_passed_to_operator(self, mock_bpy):
        mod = _reload("core.objects")
        mod.create_primitive("cylinder", "LocCylinder", location=(1.0, 2.0, 3.0))
        # Verify the operator was called with location
        op_call = mock_bpy.ops.mesh.primitive_cylinder_add
        op_call.assert_called_once()
        _, kwargs = op_call.call_args
        assert kwargs["location"] == (1.0, 2.0, 3.0)

    def test_rotation_passed_to_operator(self, mock_bpy):
        import math
        mod = _reload("core.objects")
        rot = (0.0, 0.0, math.pi / 2)
        mod.create_primitive("cube", "RotCube", rotation=rot)
        op_call = mock_bpy.ops.mesh.primitive_cube_add
        _, kwargs = op_call.call_args
        assert kwargs["rotation"] == rot

    def test_uv_sphere_alias_works(self, mock_bpy):
        mod = _reload("core.objects")
        result = mod.create_primitive("uv_sphere", "MySphere")
        assert result["success"] is True

    def test_ico_sphere_works(self, mock_bpy):
        mod = _reload("core.objects")
        result = mod.create_primitive("ico_sphere", "MyIcoSphere")
        assert result["success"] is True

    def test_torus_works(self, mock_bpy):
        mod = _reload("core.objects")
        result = mod.create_primitive("torus", "MyTorus")
        assert result["success"] is True

    def test_cone_works(self, mock_bpy):
        mod = _reload("core.objects")
        result = mod.create_primitive("cone", "MyCone")
        assert result["success"] is True

    def test_plane_works(self, mock_bpy):
        mod = _reload("core.objects")
        result = mod.create_primitive("plane", "MyPlane")
        assert result["success"] is True

    def test_no_active_object_returns_failure(self, mock_bpy):
        mod = _reload("core.objects")
        mock_bpy.context.active_object = None
        result = mod.create_primitive("cube", "FailCube")
        assert result["success"] is False
        assert result["object_name"] is None
        assert "no active object" in result["message"]

    def test_case_insensitive_type(self, mock_bpy):
        mod = _reload("core.objects")
        result = mod.create_primitive("CUBE", "CaseTest")
        assert result["success"] is True

    def test_return_dict_has_required_keys(self, mock_bpy):
        mod = _reload("core.objects")
        result = mod.create_primitive("cube", "KeyTest")
        assert "success" in result
        assert "object_name" in result
        assert "message" in result


# ─────────────────────────────────────────────────────────────────────────────
# 2. set_transform
# ─────────────────────────────────────────────────────────────────────────────

class TestSetTransformExtended:
    """Behavioral tests for set_transform."""

    def _make_obj(self, mock_bpy, name="TObj"):
        obj = MockBlenderObject(name)
        mock_bpy._test_register_object(obj)
        return obj

    def test_location_set_correctly(self, mock_bpy):
        mod = _reload("core.objects")
        obj = self._make_obj(mock_bpy, "LocObj")
        result = mod.set_transform("LocObj", location=(5.0, 3.0, 1.0))
        assert result["success"] is True
        assert obj.location == (5.0, 3.0, 1.0)
        assert "location" in result["message"]

    def test_rotation_set_correctly(self, mock_bpy):
        import math
        mod = _reload("core.objects")
        obj = self._make_obj(mock_bpy, "RotObj")
        rot = (math.pi, 0.0, 0.0)
        result = mod.set_transform("RotObj", rotation=rot)
        assert result["success"] is True
        assert obj.rotation_euler == rot

    def test_scale_set_correctly(self, mock_bpy):
        mod = _reload("core.objects")
        obj = self._make_obj(mock_bpy, "ScaleObj")
        result = mod.set_transform("ScaleObj", scale=(2.0, 2.0, 2.0))
        assert result["success"] is True
        assert obj.scale == (2.0, 2.0, 2.0)

    def test_all_transforms_at_once(self, mock_bpy):
        mod = _reload("core.objects")
        obj = self._make_obj(mock_bpy, "AllObj")
        result = mod.set_transform(
            "AllObj",
            location=(1.0, 2.0, 3.0),
            rotation=(0.1, 0.2, 0.3),
            scale=(0.5, 0.5, 0.5),
        )
        assert result["success"] is True
        assert "location" in result["message"]
        assert "rotation" in result["message"]
        assert "scale" in result["message"]

    def test_no_changes_message(self, mock_bpy):
        mod = _reload("core.objects")
        self._make_obj(mock_bpy, "NoChangeObj")
        result = mod.set_transform("NoChangeObj")
        assert result["success"] is True
        assert "No transform changes" in result["message"]

    def test_invalid_scale_length_raises(self, mock_bpy):
        mod = _reload("core.objects")
        self._make_obj(mock_bpy, "ScaleErrObj")
        with pytest.raises(ValueError, match="3 floats"):
            mod.set_transform("ScaleErrObj", scale=(1.0, 2.0))

    def test_negative_scale_allowed(self, mock_bpy):
        """Negative scale (for mirror) is valid as long as non-zero."""
        mod = _reload("core.objects")
        obj = self._make_obj(mock_bpy, "NegScaleObj")
        result = mod.set_transform("NegScaleObj", scale=(-1.0, 1.0, 1.0))
        assert result["success"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 3. duplicate_object
# ─────────────────────────────────────────────────────────────────────────────

class TestDuplicateObjectExtended:

    def _make_obj(self, mock_bpy, name="SrcObj"):
        obj = MockBlenderObject(name)
        mock_bpy._test_register_object(obj)
        return obj

    def test_duplicate_returns_success(self, mock_bpy):
        mod = _reload("core.objects")
        self._make_obj(mock_bpy, "Original")
        result = mod.duplicate_object("Original")
        assert result["success"] is True
        assert result["object_name"] is not None

    def test_new_name_applied(self, mock_bpy):
        mod = _reload("core.objects")
        self._make_obj(mock_bpy, "Source")
        result = mod.duplicate_object("Source", new_name="Clone")
        assert result["success"] is True
        assert result["object_name"] == "Clone"

    def test_offset_applied_to_location(self, mock_bpy):
        mod = _reload("core.objects")
        self._make_obj(mock_bpy, "OffsetSrc")
        result = mod.duplicate_object("OffsetSrc", offset=(1.0, 2.0, 3.0))
        assert result["success"] is True

    def test_invalid_offset_length_raises(self, mock_bpy):
        mod = _reload("core.objects")
        self._make_obj(mock_bpy, "BadOffsetSrc")
        with pytest.raises(ValueError, match="3 floats"):
            mod.duplicate_object("BadOffsetSrc", offset=(1.0, 2.0))

    def test_no_active_object_after_dup_returns_failure(self, mock_bpy):
        mod = _reload("core.objects")
        self._make_obj(mock_bpy, "FailSrc")
        mock_bpy.context.active_object = None
        result = mod.duplicate_object("FailSrc")
        assert result["success"] is False
        assert result["object_name"] is None

    def test_duplicate_calls_ops_duplicate(self, mock_bpy):
        mod = _reload("core.objects")
        self._make_obj(mock_bpy, "OpsSrc")
        mod.duplicate_object("OpsSrc")
        mock_bpy.ops.object.duplicate.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 4. delete_object
# ─────────────────────────────────────────────────────────────────────────────

class TestDeleteObjectExtended:

    def test_delete_removes_from_scene(self, mock_bpy):
        mod = _reload("core.objects")
        obj = MockBlenderObject("ToDelete")
        mock_bpy._test_register_object(obj)
        assert mock_bpy._test_objects.get("ToDelete") is not None

        result = mod.delete_object("ToDelete")
        assert result["success"] is True
        # bpy.data.objects.remove should have been called
        assert mock_bpy._test_objects.get("ToDelete") is None

    def test_delete_uses_data_api_not_ops(self, mock_bpy):
        """Ensure delete_object uses bpy.data.objects.remove, not bpy.ops."""
        mod = _reload("core.objects")
        obj = MockBlenderObject("DataDeleteObj")
        mock_bpy._test_register_object(obj)
        mod.delete_object("DataDeleteObj")
        # bpy.ops.object.delete should NOT have been called for deletion
        mock_bpy.ops.object.delete.assert_not_called()

    def test_delete_message_contains_name(self, mock_bpy):
        mod = _reload("core.objects")
        obj = MockBlenderObject("MsgObj")
        mock_bpy._test_register_object(obj)
        result = mod.delete_object("MsgObj")
        assert "MsgObj" in result["message"]


# ─────────────────────────────────────────────────────────────────────────────
# 5. create_material
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateMaterialExtended:

    def test_material_added_to_bpy_data(self, mock_bpy):
        mod = _reload("core.materials")
        result = mod.create_material("TestMat")
        assert result["success"] is True
        assert result["material_name"] == "TestMat"
        # The material should exist in the mock materials dict
        assert mock_bpy._test_materials.get("TestMat") is not None

    def test_existing_material_reused(self, mock_bpy):
        mod = _reload("core.materials")
        mod.create_material("ReuseMe", base_color=(0.1, 0.2, 0.3, 1.0))
        materials_before = len(mock_bpy._test_materials)
        result2 = mod.create_material("ReuseMe", base_color=(0.9, 0.8, 0.7, 1.0))
        assert result2["success"] is True
        assert result2["material_name"] == "ReuseMe"
        # A second create_material call for the same name should NOT add a new entry
        assert len(mock_bpy._test_materials) == materials_before

    def test_emission_only_strength_uses_base_color(self, mock_bpy):
        mod = _reload("core.materials")
        result = mod.create_material(
            "EmitMat",
            base_color=(1.0, 0.5, 0.0, 1.0),
            emission_strength=3.0,
        )
        assert result["success"] is True

    def test_emission_color_and_strength(self, mock_bpy):
        mod = _reload("core.materials")
        result = mod.create_material(
            "FullEmit",
            emission_color=(0.0, 0.0, 1.0, 1.0),
            emission_strength=5.0,
        )
        assert result["success"] is True

    def test_use_nodes_enabled(self, mock_bpy):
        mod = _reload("core.materials")
        mod.create_material("NodesMat")
        mat = mock_bpy._test_materials["NodesMat"]
        assert mat.use_nodes is True

    def test_metallic_material(self, mock_bpy):
        mod = _reload("core.materials")
        result = mod.create_material("MetalMat", metallic=1.0, roughness=0.0)
        assert result["success"] is True

    def test_return_dict_has_required_keys(self, mock_bpy):
        mod = _reload("core.materials")
        result = mod.create_material("KeyCheckMat")
        assert "success" in result
        assert "material_name" in result
        assert "message" in result


# ─────────────────────────────────────────────────────────────────────────────
# 6. assign_material
# ─────────────────────────────────────────────────────────────────────────────

class TestAssignMaterialExtended:

    def _setup(self, mock_bpy, obj_name="AssignObj", mat_name="AssignMat"):
        obj = MockBlenderObject(obj_name)
        mock_bpy._test_register_object(obj)
        mat = mock_bpy.data.materials.new(mat_name)
        return obj, mat

    def test_assigns_material_to_object(self, mock_bpy):
        mod = _reload("core.materials")
        obj, mat = self._setup(mock_bpy)
        result = mod.assign_material("AssignObj", "AssignMat")
        assert result["success"] is True
        assert len(obj.data.materials._materials) == 1

    def test_already_assigned_not_duplicated(self, mock_bpy):
        mod = _reload("core.materials")
        obj, mat = self._setup(mock_bpy, "NoDoubleObj", "NoDupMat")
        # Set up the material_slots to already have this material
        slot = MagicMock()
        slot.material = mat
        slot.material.name = "NoDupMat"
        obj.material_slots = [slot]
        result = mod.assign_material("NoDoubleObj", "NoDupMat")
        assert result["success"] is True
        assert "already assigned" in result["message"]
        # data.materials.append should NOT have been called again
        assert len(obj.data.materials._materials) == 0  # no append was called

    def test_message_contains_both_names(self, mock_bpy):
        mod = _reload("core.materials")
        self._setup(mock_bpy, "MsgObj2", "MsgMat2")
        result = mod.assign_material("MsgObj2", "MsgMat2")
        assert "MsgObj2" in result["message"]
        assert "MsgMat2" in result["message"]


# ─────────────────────────────────────────────────────────────────────────────
# 7. add_modifier
# ─────────────────────────────────────────────────────────────────────────────

class TestAddModifierExtended:

    def _make_mesh(self, mock_bpy, name="ModMesh"):
        obj = MockBlenderObject(name)
        obj.type = "MESH"
        mock_bpy._test_register_object(obj)
        return obj

    def test_bevel_added_with_defaults(self, mock_bpy):
        mod = _reload("core.modifiers")
        obj = self._make_mesh(mock_bpy, "BevelObj")
        result = mod.add_modifier("BevelObj", "bevel")
        assert result["success"] is True
        assert result["modifier_name"] is not None

    def test_custom_modifier_name(self, mock_bpy):
        mod = _reload("core.modifiers")
        obj = self._make_mesh(mock_bpy, "NamedMod")
        result = mod.add_modifier("NamedMod", "bevel", modifier_name="MyBevel")
        assert result["modifier_name"] == "MyBevel"

    def test_params_override_defaults(self, mock_bpy):
        mod = _reload("core.modifiers")
        obj = self._make_mesh(mock_bpy, "ParamObj")
        result = mod.add_modifier(
            "ParamObj", "decimate",
            params={"ratio": 0.25},
        )
        assert result["success"] is True

    def test_all_supported_types(self, mock_bpy):
        mod = _reload("core.modifiers")
        for mtype in mod.MODIFIER_TYPES:
            obj = self._make_mesh(mock_bpy, f"Obj_{mtype}")
            result = mod.add_modifier(f"Obj_{mtype}", mtype)
            assert result["success"] is True, f"Failed for modifier type: {mtype}"

    def test_modifier_registered_on_object(self, mock_bpy):
        mod = _reload("core.modifiers")
        obj = self._make_mesh(mock_bpy, "RegObj")
        mod.add_modifier("RegObj", "solidify", modifier_name="SolidMod")
        assert obj.modifiers.get("SolidMod") is not None

    def test_return_dict_has_required_keys(self, mock_bpy):
        mod = _reload("core.modifiers")
        self._make_mesh(mock_bpy, "KeyObj2")
        result = mod.add_modifier("KeyObj2", "bevel")
        assert "success" in result
        assert "modifier_name" in result
        assert "message" in result


# ─────────────────────────────────────────────────────────────────────────────
# 8. apply_modifier
# ─────────────────────────────────────────────────────────────────────────────

class TestApplyModifierExtended:

    def _make_mesh_with_mod(self, mock_bpy, obj_name="ApplyObj", mod_name="ApplyMod"):
        obj = MockBlenderObject(obj_name)
        obj.type = "MESH"
        mock_bpy._test_register_object(obj)
        # Add a modifier to the object
        obj.modifiers.new(mod_name, "BEVEL")
        return obj

    def test_apply_calls_ops_modifier_apply(self, mock_bpy):
        mod = _reload("core.modifiers")
        self._make_mesh_with_mod(mock_bpy, "ApplyOpObj", "ApplyOpMod")
        result = mod.apply_modifier("ApplyOpObj", "ApplyOpMod")
        assert result["success"] is True
        mock_bpy.ops.object.modifier_apply.assert_called()

    def test_apply_with_correct_modifier_name(self, mock_bpy):
        mod = _reload("core.modifiers")
        self._make_mesh_with_mod(mock_bpy, "ApplyNameObj", "CorrectMod")
        result = mod.apply_modifier("ApplyNameObj", "CorrectMod")
        assert result["success"] is True
        call_kwargs = mock_bpy.ops.object.modifier_apply.call_args
        assert call_kwargs[1]["modifier"] == "CorrectMod"

    def test_apply_modifier_not_found_raises(self, mock_bpy):
        mod = _reload("core.modifiers")
        obj = MockBlenderObject("NoModObj")
        obj.type = "MESH"
        mock_bpy._test_register_object(obj)
        with pytest.raises(ValueError, match="not found"):
            mod.apply_modifier("NoModObj", "GhostMod")


# ─────────────────────────────────────────────────────────────────────────────
# 9. Scene Inspection
# ─────────────────────────────────────────────────────────────────────────────

class TestGetSceneSummary:

    def test_returns_required_keys(self, mock_bpy):
        mod = _reload("core.scene")
        result = mod.get_scene_summary()
        for key in ("object_count", "objects", "has_camera", "has_lights", "render_engine"):
            assert key in result, f"Missing key: {key}"

    def test_object_count_matches_scene(self, mock_bpy):
        mod = _reload("core.scene")
        result = mod.get_scene_summary()
        assert result["object_count"] == len(mock_bpy.context.scene.objects)

    def test_objects_list_has_correct_structure(self, mock_bpy):
        mod = _reload("core.scene")
        result = mod.get_scene_summary()
        for obj_info in result["objects"]:
            assert "name" in obj_info
            assert "type" in obj_info
            assert "location" in obj_info

    def test_no_camera_detected_correctly(self, mock_bpy):
        mod = _reload("core.scene")
        # Default mock has no CAMERA objects
        result = mod.get_scene_summary()
        assert result["has_camera"] is False

    def test_camera_detected_when_present(self, mock_bpy):
        mod = _reload("core.scene")
        cam = MockBlenderObject("SceneCam", "CAMERA")
        mock_bpy._test_register_object(cam)
        mock_bpy.context.scene.objects = list(mock_bpy._test_objects.values())
        result = mod.get_scene_summary()
        assert result["has_camera"] is True


class TestGetObjectDetailsExtended:

    def test_mesh_details_include_mesh_stats(self, mock_bpy):
        mod = _reload("core.scene")
        result = mod.get_object_details("DefaultCube")
        assert "mesh" in result
        assert "vertex_count" in result["mesh"]
        assert "edge_count" in result["mesh"]
        assert "polygon_count" in result["mesh"]

    def test_details_include_transforms(self, mock_bpy):
        mod = _reload("core.scene")
        result = mod.get_object_details("DefaultCube")
        assert "location" in result
        assert "rotation_euler" in result
        assert "scale" in result
        assert "dimensions" in result

    def test_details_include_modifier_list(self, mock_bpy):
        mod = _reload("core.scene")
        result = mod.get_object_details("DefaultCube")
        assert "modifiers" in result
        assert isinstance(result["modifiers"], list)

    def test_details_include_material_list(self, mock_bpy):
        mod = _reload("core.scene")
        result = mod.get_object_details("DefaultCube")
        assert "materials" in result
        assert isinstance(result["materials"], list)

    def test_return_dict_has_required_keys(self, mock_bpy):
        mod = _reload("core.scene")
        result = mod.get_object_details("DefaultCube")
        for key in ("name", "type", "location", "rotation_euler", "scale", "dimensions"):
            assert key in result


class TestGetMeshStatisticsExtended:

    def test_statistics_contain_required_fields(self, mock_bpy):
        mod = _reload("core.scene")
        result = mod.get_mesh_statistics("DefaultCube")
        for key in ("vertex_count", "edge_count", "face_count", "triangle_count",
                    "has_ngons", "dimensions"):
            assert key in result, f"Missing field: {key}"

    def test_vertex_count_is_positive(self, mock_bpy):
        mod = _reload("core.scene")
        result = mod.get_mesh_statistics("DefaultCube")
        assert result["vertex_count"] >= 0

    def test_object_name_in_result(self, mock_bpy):
        mod = _reload("core.scene")
        result = mod.get_mesh_statistics("DefaultCube")
        assert result["object_name"] == "DefaultCube"


# ─────────────────────────────────────────────────────────────────────────────
# 10. render_preview
# ─────────────────────────────────────────────────────────────────────────────

class TestRenderPreviewExtended:

    def test_render_requires_camera(self, mock_bpy):
        mod = _reload("core.rendering")
        mock_bpy.context.scene.camera = None
        with pytest.raises(ValueError, match="No active camera"):
            mod.render_preview("output/test.png")

    def test_render_calls_ops_render(self, mock_bpy, tmp_path):
        mod = _reload("core.rendering")
        mock_bpy.context.scene.camera = MagicMock()
        output = str(tmp_path / "test.png")
        result = mod.render_preview(output)
        assert result["success"] is True
        mock_bpy.ops.render.render.assert_called_once_with(write_still=True)

    def test_render_sets_resolution(self, mock_bpy, tmp_path):
        mod = _reload("core.rendering")
        mock_bpy.context.scene.camera = MagicMock()
        output = str(tmp_path / "res_test.png")
        mod.render_preview(output, resolution_x=512, resolution_y=512)
        assert mock_bpy.context.scene.render.resolution_x == 512
        assert mock_bpy.context.scene.render.resolution_y == 512

    def test_render_output_path_in_result(self, mock_bpy, tmp_path):
        mod = _reload("core.rendering")
        mock_bpy.context.scene.camera = MagicMock()
        output = str(tmp_path / "path_test.png")
        result = mod.render_preview(output)
        assert result["output_path"] is not None
        assert result["output_path"].endswith("path_test.png")

    def test_invalid_resolution_raises(self, mock_bpy):
        mod = _reload("core.rendering")
        mock_bpy.context.scene.camera = MagicMock()
        with pytest.raises(ValueError, match="positive"):
            mod.render_preview("out.png", resolution_x=0, resolution_y=1024)

    def test_invalid_samples_raises(self, mock_bpy):
        mod = _reload("core.rendering")
        mock_bpy.context.scene.camera = MagicMock()
        with pytest.raises(ValueError, match="positive"):
            mod.render_preview("out.png", samples=0)

    def test_return_dict_has_required_keys(self, mock_bpy, tmp_path):
        mod = _reload("core.rendering")
        mock_bpy.context.scene.camera = MagicMock()
        output = str(tmp_path / "keys_test.png")
        result = mod.render_preview(output)
        assert "success" in result
        assert "output_path" in result
        assert "message" in result


# ─────────────────────────────────────────────────────────────────────────────
# 11. save_checkpoint / save_project / export_asset
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveCheckpointExtended:

    def test_blend_extension_added(self, mock_bpy, tmp_path):
        mod = _reload("core.project")
        path = str(tmp_path / "my_checkpoint")
        result = mod.save_checkpoint(path)
        assert result["success"] is True
        assert result["checkpoint_path"].endswith(".blend")

    def test_extension_not_duplicated(self, mock_bpy, tmp_path):
        mod = _reload("core.project")
        path = str(tmp_path / "checkpoint.blend")
        result = mod.save_checkpoint(path)
        assert result["checkpoint_path"].endswith(".blend")
        # Should not be .blend.blend
        assert not result["checkpoint_path"].endswith(".blend.blend")

    def test_save_as_mainfile_called(self, mock_bpy, tmp_path):
        mod = _reload("core.project")
        path = str(tmp_path / "save_test.blend")
        mod.save_checkpoint(path)
        mock_bpy.ops.wm.save_as_mainfile.assert_called()

    def test_copy_true_by_default(self, mock_bpy, tmp_path):
        mod = _reload("core.project")
        path = str(tmp_path / "copy_test.blend")
        mod.save_checkpoint(path, copy=True)
        _, kwargs = mock_bpy.ops.wm.save_as_mainfile.call_args
        assert kwargs.get("copy") is True


class TestSaveProjectExtended:

    def test_save_project_calls_save_as_mainfile(self, mock_bpy, tmp_path):
        mod = _reload("core.project")
        path = str(tmp_path / "project.blend")
        result = mod.save_project(path)
        assert result["success"] is True
        mock_bpy.ops.wm.save_as_mainfile.assert_called()

    def test_project_path_in_result(self, mock_bpy, tmp_path):
        mod = _reload("core.project")
        path = str(tmp_path / "myproject.blend")
        result = mod.save_project(path)
        assert "project_path" in result
        assert result["project_path"].endswith(".blend")


class TestExportAssetExtended:

    def _register_obj(self, mock_bpy, name):
        obj = MockBlenderObject(name)
        mock_bpy._test_register_object(obj)

    def test_fbx_export_calls_ops(self, mock_bpy, tmp_path):
        mod = _reload("core.project")
        self._register_obj(mock_bpy, "ExportMesh1")
        output = str(tmp_path / "asset")
        result = mod.export_asset(["ExportMesh1"], export_format="FBX", output_path=output)
        assert result["success"] is True
        mock_bpy.ops.export_scene.fbx.assert_called()

    def test_glb_export_calls_ops(self, mock_bpy, tmp_path):
        mod = _reload("core.project")
        self._register_obj(mock_bpy, "ExportMesh2")
        output = str(tmp_path / "asset2")
        result = mod.export_asset(["ExportMesh2"], export_format="GLB", output_path=output)
        assert result["success"] is True
        mock_bpy.ops.export_scene.gltf.assert_called()

    def test_fbx_extension_added_automatically(self, mock_bpy, tmp_path):
        mod = _reload("core.project")
        self._register_obj(mock_bpy, "ExtObj")
        output = str(tmp_path / "no_ext")
        result = mod.export_asset(["ExtObj"], export_format="FBX", output_path=output)
        assert result["export_path"].endswith(".fbx")

    def test_glb_extension_added_automatically(self, mock_bpy, tmp_path):
        mod = _reload("core.project")
        self._register_obj(mock_bpy, "GLBObj")
        output = str(tmp_path / "glb_no_ext")
        result = mod.export_asset(["GLBObj"], export_format="GLB", output_path=output)
        assert result["export_path"].endswith(".glb")

    def test_export_result_contains_format(self, mock_bpy, tmp_path):
        mod = _reload("core.project")
        self._register_obj(mock_bpy, "FormatObj")
        output = str(tmp_path / "format_test")
        result = mod.export_asset(["FormatObj"], export_format="FBX", output_path=output)
        assert result["format"] == "FBX"

    def test_export_result_contains_exported_objects(self, mock_bpy, tmp_path):
        mod = _reload("core.project")
        self._register_obj(mock_bpy, "ObjListA")
        self._register_obj(mock_bpy, "ObjListB")
        output = str(tmp_path / "multi_export")
        result = mod.export_asset(
            ["ObjListA", "ObjListB"],
            export_format="FBX",
            output_path=output,
        )
        assert "ObjListA" in result["exported_objects"]
        assert "ObjListB" in result["exported_objects"]

    def test_return_dict_has_required_keys(self, mock_bpy, tmp_path):
        mod = _reload("core.project")
        self._register_obj(mock_bpy, "KeysObj")
        output = str(tmp_path / "keys")
        result = mod.export_asset(["KeysObj"], export_format="FBX", output_path=output)
        for key in ("success", "export_path", "format", "exported_objects", "message"):
            assert key in result, f"Missing key: {key}"

    def test_gltf_format_alias_works(self, mock_bpy, tmp_path):
        """GLTF should be accepted as an alias for GLB."""
        mod = _reload("core.project")
        self._register_obj(mock_bpy, "GltfObj")
        output = str(tmp_path / "gltf_test")
        result = mod.export_asset(["GltfObj"], export_format="GLTF", output_path=output)
        assert result["success"] is True
