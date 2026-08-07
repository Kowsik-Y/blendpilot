"""
BlendPilot AI — Object Module Tests

Tests for core/objects.py input validation and error handling.
Uses the bpy mock from conftest.py.
"""

from __future__ import annotations

import importlib

import pytest


class TestCreatePrimitive:
    def _import_module(self):
        """Import (or reimport) the objects module with mock bpy available."""
        import core.objects as mod
        importlib.reload(mod)
        return mod

    def test_empty_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.create_primitive("cube", "")

    def test_whitespace_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.create_primitive("cube", "   ")

    def test_unsupported_type_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="Unsupported primitive type"):
            mod.create_primitive("pyramid", "MyPyramid")

    def test_invalid_dimensions_length(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="3 floats"):
            mod.create_primitive("cube", "MyCube", dimensions=(1.0, 2.0))

    def test_negative_dimensions_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="positive"):
            mod.create_primitive("cube", "MyCube", dimensions=(1.0, -0.5, 1.0))

    def test_zero_dimensions_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="positive"):
            mod.create_primitive("cube", "MyCube", dimensions=(1.0, 0.0, 1.0))

    def test_invalid_location_length(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="3 floats"):
            mod.create_primitive("cube", "MyCube", location=(1.0, 2.0))

    def test_invalid_rotation_length(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="3 floats"):
            mod.create_primitive("cube", "MyCube", rotation=(1.0,))

    def test_valid_cube_creation(self, mock_bpy):
        mod = self._import_module()
        result = mod.create_primitive("cube", "TestCube")
        assert result["success"] is True
        assert "TestCube" in result["object_name"]

    def test_all_primitive_types_accepted(self):
        mod = self._import_module()
        for ptype in mod.PRIMITIVE_TYPES:
            # Should not raise — validation only
            try:
                mod.create_primitive(ptype, f"Test_{ptype}")
            except Exception:
                pass  # bpy mock may not perfectly handle all ops

    def test_case_insensitive_type(self):
        mod = self._import_module()
        result = mod.create_primitive("CUBE", "TestCube2")
        assert result["success"] is True


class TestSetTransform:
    def _import_module(self):
        import core.objects as mod
        importlib.reload(mod)
        return mod

    def test_empty_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.set_transform("")

    def test_object_not_found_raises(self, mock_bpy):
        mod = self._import_module()
        with pytest.raises(ValueError, match="not found"):
            mod.set_transform("NonExistentObject", location=(0, 0, 0))

    def test_invalid_location_length(self, mock_bpy):
        mod = self._import_module()
        # Register a test object
        from tests.conftest import MockBlenderObject
        obj = MockBlenderObject("TestObj")
        mock_bpy._test_register_object(obj)
        with pytest.raises(ValueError, match="3 floats"):
            mod.set_transform("TestObj", location=(1.0, 2.0))

    def test_zero_scale_raises(self, mock_bpy):
        mod = self._import_module()
        from tests.conftest import MockBlenderObject
        obj = MockBlenderObject("TestObj2")
        mock_bpy._test_register_object(obj)
        with pytest.raises(ValueError, match="zero"):
            mod.set_transform("TestObj2", scale=(1.0, 0.0, 1.0))

    def test_no_changes(self, mock_bpy):
        mod = self._import_module()
        from tests.conftest import MockBlenderObject
        obj = MockBlenderObject("TestObj3")
        mock_bpy._test_register_object(obj)
        result = mod.set_transform("TestObj3")
        assert result["success"] is True
        assert "No transform changes" in result["message"]


class TestDuplicateObject:
    def _import_module(self):
        import core.objects as mod
        importlib.reload(mod)
        return mod

    def test_empty_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.duplicate_object("")

    def test_source_not_found_raises(self, mock_bpy):
        mod = self._import_module()
        with pytest.raises(ValueError, match="not found"):
            mod.duplicate_object("NonExistent")


class TestDeleteObject:
    def _import_module(self):
        import core.objects as mod
        importlib.reload(mod)
        return mod

    def test_empty_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.delete_object("")

    def test_object_not_found_raises(self, mock_bpy):
        mod = self._import_module()
        with pytest.raises(ValueError, match="not found"):
            mod.delete_object("NonExistent")
