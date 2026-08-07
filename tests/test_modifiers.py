"""
BlendPilot AI — Modifier Module Tests

Tests for core/modifiers.py input validation and error handling.
"""

from __future__ import annotations

import importlib

import pytest

from tests.conftest import MockBlenderObject


class TestAddModifier:
    def _import_module(self):
        import core.modifiers as mod
        importlib.reload(mod)
        return mod

    def test_empty_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.add_modifier("", "bevel")

    def test_unsupported_type_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="Unsupported modifier type"):
            mod.add_modifier("SomeObject", "warp_drive")

    def test_object_not_found_raises(self, mock_bpy):
        mod = self._import_module()
        with pytest.raises(ValueError, match="not found"):
            mod.add_modifier("NonExistent", "bevel")

    def test_non_mesh_object_raises(self, mock_bpy):
        mod = self._import_module()
        cam = MockBlenderObject("TestCamera", "CAMERA")
        mock_bpy._test_register_object(cam)
        with pytest.raises(ValueError, match="not MESH"):
            mod.add_modifier("TestCamera", "bevel")

    def test_valid_bevel(self, mock_bpy):
        mod = self._import_module()
        obj = MockBlenderObject("TestMesh")
        mock_bpy._test_register_object(obj)
        result = mod.add_modifier("TestMesh", "bevel")
        assert result["success"] is True
        assert "BEVEL" in result["message"]

    def test_custom_params(self, mock_bpy):
        mod = self._import_module()
        obj = MockBlenderObject("ParamMesh")
        mock_bpy._test_register_object(obj)
        result = mod.add_modifier(
            "ParamMesh", "bevel",
            modifier_name="MyBevel",
            params={"width": 0.05, "segments": 3},
        )
        assert result["success"] is True
        assert result["modifier_name"] == "MyBevel"

    def test_all_supported_types(self, mock_bpy):
        mod = self._import_module()
        for mtype in mod.MODIFIER_TYPES:
            obj = MockBlenderObject(f"Obj_{mtype}")
            mock_bpy._test_register_object(obj)
            result = mod.add_modifier(f"Obj_{mtype}", mtype)
            assert result["success"] is True


class TestApplyModifier:
    def _import_module(self):
        import core.modifiers as mod
        importlib.reload(mod)
        return mod

    def test_empty_object_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="Object name cannot be empty"):
            mod.apply_modifier("", "SomeMod")

    def test_empty_modifier_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="Modifier name cannot be empty"):
            mod.apply_modifier("SomeObj", "")

    def test_object_not_found_raises(self, mock_bpy):
        mod = self._import_module()
        with pytest.raises(ValueError, match="not found"):
            mod.apply_modifier("NonExistent", "SomeMod")

    def test_modifier_not_found_raises(self, mock_bpy):
        mod = self._import_module()
        obj = MockBlenderObject("ApplyTest")
        mock_bpy._test_register_object(obj)
        with pytest.raises(ValueError, match="not found on"):
            mod.apply_modifier("ApplyTest", "NonExistentMod")
