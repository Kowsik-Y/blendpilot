"""
BlendPilot — Project Module Tests

Tests for core/project.py input validation.
"""

from __future__ import annotations

import importlib

import pytest


class TestSaveCheckpoint:
    def _import_module(self):
        import core.project as mod
        importlib.reload(mod)
        return mod

    def test_empty_path_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="path cannot be empty"):
            mod.save_checkpoint("")


class TestRestoreCheckpoint:
    def _import_module(self):
        import core.project as mod
        importlib.reload(mod)
        return mod

    def test_empty_path_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="path cannot be empty"):
            mod.restore_checkpoint("")

    def test_file_not_found_raises(self):
        mod = self._import_module()
        with pytest.raises(FileNotFoundError):
            mod.restore_checkpoint("/nonexistent/path/checkpoint.blend")


class TestSaveProject:
    def _import_module(self):
        import core.project as mod
        importlib.reload(mod)
        return mod

    def test_empty_path_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="path cannot be empty"):
            mod.save_project("")


class TestExportAsset:
    def _import_module(self):
        import core.project as mod
        importlib.reload(mod)
        return mod

    def test_empty_object_list_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="At least one"):
            mod.export_asset([], output_path="test.fbx")

    def test_unsupported_format_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="Unsupported export format"):
            mod.export_asset(["Obj"], export_format="OBJ",
                             output_path="test.obj")

    def test_empty_output_path_raises(self):
        mod = self._import_module()
        with pytest.raises(ValueError, match="Output path cannot be empty"):
            mod.export_asset(["Obj"], output_path="")

    def test_missing_objects_raises(self, mock_bpy):
        mod = self._import_module()
        with pytest.raises(ValueError, match="not found"):
            mod.export_asset(["NonExistent1", "NonExistent2"],
                             output_path="test.fbx")
