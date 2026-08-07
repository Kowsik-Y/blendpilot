"""
BlendPilot AI — Scene Module Tests

Tests for core/scene.py input validation.
"""

from __future__ import annotations

import importlib

import pytest

from tests.conftest import MockBlenderObject


class TestGetObjectDetails:
    def _import_module(self):
        import core.scene as mod
        importlib.reload(mod)
        return mod

    def test_empty_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.get_object_details("")

    def test_object_not_found_raises(self, mock_bpy):
        mod = self._import_module()
        with pytest.raises(ValueError, match="not found"):
            mod.get_object_details("NonExistent")


class TestGetMeshStatistics:
    def _import_module(self):
        import core.scene as mod
        importlib.reload(mod)
        return mod

    def test_empty_name_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="name cannot be empty"):
            mod.get_mesh_statistics("")

    def test_object_not_found_raises(self, mock_bpy):
        mod = self._import_module()
        with pytest.raises(ValueError, match="not found"):
            mod.get_mesh_statistics("NonExistent")

    def test_non_mesh_raises(self, mock_bpy):
        mod = self._import_module()
        cam = MockBlenderObject("TestCam", "CAMERA")
        mock_bpy._test_register_object(cam)
        with pytest.raises(ValueError, match="not MESH"):
            mod.get_mesh_statistics("TestCam")
