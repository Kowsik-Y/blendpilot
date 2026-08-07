"""
BlendPilot AI — Material Module Tests

Tests for core/materials.py input validation and error handling.
"""

from __future__ import annotations

import importlib

import pytest

from tests.conftest import MockBlenderObject


class TestCreateMaterial:
    def _import_module(self):
        import core.materials as mod
        importlib.reload(mod)
        return mod

    def test_empty_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.create_material("")

    def test_invalid_base_color_length(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="4 floats"):
            mod.create_material("TestMat", base_color=(1.0, 0.0, 0.0))

    def test_base_color_out_of_range(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            mod.create_material("TestMat", base_color=(1.5, 0.0, 0.0, 1.0))

    def test_metallic_out_of_range(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="Metallic"):
            mod.create_material("TestMat", metallic=1.5)

    def test_roughness_out_of_range(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="Roughness"):
            mod.create_material("TestMat", roughness=-0.1)

    def test_negative_emission_strength(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="Emission strength"):
            mod.create_material("TestMat", emission_strength=-1.0)

    def test_invalid_emission_color_length(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="4 floats"):
            mod.create_material("TestMat", emission_color=(0.0, 0.5, 1.0))

    def test_valid_material_creation(self, mock_bpy):
        mod = self._import_module()
        result = mod.create_material(
            "RedMaterial",
            base_color=(0.8, 0.1, 0.1, 1.0),
            metallic=0.0,
            roughness=0.4,
        )
        assert result["success"] is True
        assert "RedMaterial" in result["material_name"]

    def test_emissive_material(self, mock_bpy):
        mod = self._import_module()
        result = mod.create_material(
            "GlowMat",
            base_color=(0.0, 0.5, 1.0, 1.0),
            emission_color=(0.0, 0.5, 1.0, 1.0),
            emission_strength=5.0,
        )
        assert result["success"] is True


class TestAssignMaterial:
    def _import_module(self):
        import core.materials as mod
        importlib.reload(mod)
        return mod

    def test_empty_object_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="Object name cannot be empty"):
            mod.assign_material("", "SomeMat")

    def test_empty_material_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="Material name cannot be empty"):
            mod.assign_material("SomeObj", "")

    def test_object_not_found_raises(self, mock_bpy):
        mod = self._import_module()
        with pytest.raises(ValueError, match="not found"):
            mod.assign_material("NonExistent", "SomeMat")

    def test_material_not_found_raises(self, mock_bpy):
        mod = self._import_module()
        obj = MockBlenderObject("MatTestObj")
        mock_bpy._test_register_object(obj)
        with pytest.raises(ValueError, match="not found"):
            mod.assign_material("MatTestObj", "NonExistentMat")

    def test_non_mesh_object_raises(self, mock_bpy):
        mod = self._import_module()
        cam = MockBlenderObject("MatCam", "CAMERA")
        mock_bpy._test_register_object(cam)
        # Register a material
        mock_bpy._test_materials["TestMat"] = object()
        with pytest.raises(ValueError, match="not MESH"):
            mod.assign_material("MatCam", "TestMat")
