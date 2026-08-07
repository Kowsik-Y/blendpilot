"""
BlendPilot AI — Validation Module Tests

Tests for core/validation.py input validation.
"""

from __future__ import annotations

import importlib

import pytest

from tests.conftest import MockBlenderObject


class TestCheckTriangleCount:
    def _import_module(self):
        import core.validation as mod
        importlib.reload(mod)
        return mod

    def test_empty_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.check_triangle_count("")

    def test_object_not_found_raises(self, mock_bpy):
        mod = self._import_module()
        with pytest.raises(ValueError, match="not found"):
            mod.check_triangle_count("NonExistent")

    def test_non_mesh_raises(self, mock_bpy):
        mod = self._import_module()
        cam = MockBlenderObject("ValCam", "CAMERA")
        mock_bpy._test_register_object(cam)
        with pytest.raises(ValueError, match="not MESH"):
            mod.check_triangle_count("ValCam")


class TestCheckNormals:
    def _import_module(self):
        import core.validation as mod
        importlib.reload(mod)
        return mod

    def test_empty_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.check_normals("")


class TestCheckNonManifold:
    def _import_module(self):
        import core.validation as mod
        importlib.reload(mod)
        return mod

    def test_empty_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.check_non_manifold("")


class TestCheckTransforms:
    def _import_module(self):
        import core.validation as mod
        importlib.reload(mod)
        return mod

    def test_empty_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.check_transforms("")

    def test_object_not_found_raises(self, mock_bpy):
        mod = self._import_module()
        with pytest.raises(ValueError, match="not found"):
            mod.check_transforms("NonExistent")

    def test_identity_transform_passes(self, mock_bpy):
        mod = self._import_module()
        obj = MockBlenderObject("IdentityObj")
        mock_bpy._test_register_object(obj)
        result = mod.check_transforms("IdentityObj")
        assert result["passed"] is True


class TestValidateAsset:
    def _import_module(self):
        import core.validation as mod
        importlib.reload(mod)
        return mod

    def test_empty_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.validate_asset("")

    def test_non_mesh_raises(self, mock_bpy):
        mod = self._import_module()
        cam = MockBlenderObject("ValCam2", "CAMERA")
        mock_bpy._test_register_object(cam)
        with pytest.raises(ValueError, match="not MESH"):
            mod.validate_asset("ValCam2")
