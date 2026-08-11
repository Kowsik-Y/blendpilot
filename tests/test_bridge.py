"""
BlendPilot AI — Bridge & Operator Tests

Tests for the bridge server schemas, operator registry,
and command handler validation — all outside Blender.
"""

from __future__ import annotations

import importlib
import json

import pytest

from blender_addon.schemas import (
    BridgeCommand,
    BridgeResponse,
    CommandName,
    HealthResponse,
    Timer,
)


# ── Schema Tests ────────────────────────────────────────────


class TestBridgeCommand:
    def test_minimal_command(self):
        cmd = BridgeCommand(command="create_primitive")
        assert cmd.command == "create_primitive"
        assert cmd.request_id.startswith("req_")
        assert cmd.parameters == {}

    def test_full_command(self):
        cmd = BridgeCommand(
            command="create_primitive",
            request_id="req_test123",
            parameters={
                "primitive_type": "cube",
                "name": "TestCube",
                "dimensions": [1.0, 1.0, 1.0],
            },
        )
        assert cmd.request_id == "req_test123"
        assert cmd.parameters["primitive_type"] == "cube"

    def test_validate_known_command(self):
        cmd = BridgeCommand(command="create_primitive")
        assert cmd.validate_command_name() is True

    def test_validate_unknown_command(self):
        cmd = BridgeCommand(command="fly_to_mars")
        assert cmd.validate_command_name() is False

    def test_json_roundtrip(self):
        cmd = BridgeCommand(
            command="set_transform",
            parameters={"name": "Cube", "location": [1, 2, 3]},
        )
        json_str = cmd.model_dump_json()
        restored = BridgeCommand.model_validate_json(json_str)
        assert restored.command == cmd.command
        assert restored.parameters == cmd.parameters


class TestBridgeResponse:
    def test_ok_response(self):
        resp = BridgeResponse.ok(
            request_id="req_001",
            result={"object_name": "TestCube"},
            elapsed_ms=12.5,
        )
        assert resp.success is True
        assert resp.result["object_name"] == "TestCube"
        assert resp.execution_time_ms == 12.5

    def test_error_response(self):
        resp = BridgeResponse.from_error(
            request_id="req_002",
            message="Object not found.",
            elapsed_ms=1.0,
        )
        assert resp.success is False
        assert resp.error == "Object not found."
        assert resp.result is None


class TestCommandName:
    def test_all_commands_present(self):
        """Verify all expected command categories exist."""
        names = [e.value for e in CommandName]
        assert "create_primitive" in names
        assert "set_transform" in names
        assert "add_modifier" in names
        assert "create_material" in names
        assert "render_preview" in names
        assert "validate_asset" in names
        assert "save_checkpoint" in names
        assert "export_asset" in names
        assert "get_scene_summary" in names

    def test_command_count(self):
        """Ensure we have exactly 23 commands."""
        assert len(CommandName) == 23


class TestHealthResponse:
    def test_default_health(self):
        health = HealthResponse(blender_version="4.0.0")
        assert health.status == "ok"
        assert health.addon_version == "0.1.0"


class TestTimer:
    def test_measures_time(self):
        import time
        with Timer() as t:
            time.sleep(0.01)
        assert t.elapsed_ms > 0


# ── Operator Registry Tests ─────────────────────────────────


class TestOperatorRegistry:
    def test_register_and_lookup(self):
        from blender_addon.operators import COMMAND_REGISTRY, register_command, get_handler

        # Clear and register a test handler
        test_key = "__test_command__"
        COMMAND_REGISTRY.pop(test_key, None)

        def dummy_handler(params):
            return {"result": "ok"}

        register_command(test_key, dummy_handler)
        assert get_handler(test_key) is dummy_handler

        # Cleanup
        COMMAND_REGISTRY.pop(test_key, None)

    def test_unknown_command_returns_none(self):
        from blender_addon.operators import get_handler

        assert get_handler("nonexistent_command_xyz") is None

    def test_list_commands(self):
        from blender_addon.operators import list_commands

        cmds = list_commands()
        assert isinstance(cmds, list)


# ── Object Operator Tests (with mock bpy) ───────────────────


class TestObjectOperators:
    def _setup(self):
        """Import and reload the operators module."""
        import blender_addon.operators.objects as ops
        importlib.reload(ops)
        ops.register()
        return ops

    def test_handle_create_primitive_valid(self, mock_bpy):
        ops = self._setup()
        result = ops.handle_create_primitive({
            "primitive_type": "cube",
            "name": "TestCube",
            "dimensions": [1.0, 2.0, 3.0],
            "location": [0.0, 0.0, 0.0],
        })
        assert result["success"] is True

    def test_handle_create_primitive_missing_name_raises(self, mock_bpy):
        ops = self._setup()
        with pytest.raises(ValueError):
            ops.handle_create_primitive({
                "primitive_type": "cube",
                "name": "",
            })

    def test_handle_delete_object_not_found(self, mock_bpy):
        ops = self._setup()
        with pytest.raises(ValueError, match="not found"):
            ops.handle_delete_object({"name": "DoesNotExist"})


# ── Material Operator Tests ─────────────────────────────────


class TestMaterialOperators:
    def _setup(self):
        import blender_addon.operators.materials as ops
        importlib.reload(ops)
        ops.register()
        return ops

    def test_handle_create_material_valid(self, mock_bpy):
        ops = self._setup()
        result = ops.handle_create_material({
            "name": "TestMat",
            "base_color": [0.8, 0.1, 0.1, 1.0],
            "metallic": 0.0,
            "roughness": 0.4,
        })
        assert result["success"] is True

    def test_handle_create_material_empty_name(self, mock_bpy):
        ops = self._setup()
        with pytest.raises(ValueError, match="name cannot be empty"):
            ops.handle_create_material({"name": ""})


# ── Project Operator Tests ─────────────────────────────────


class TestProjectOperators:
    def _setup(self):
        import blender_addon.operators.export as ops
        importlib.reload(ops)
        ops.register()
        return ops

    def test_handle_save_checkpoint_accepts_filepath(self, mock_bpy):
        ops = self._setup()
        result = ops.handle_save_checkpoint({"filepath": "output/checkpoints/test"})
        assert result["success"] is True

    def test_handle_save_project_accepts_filepath(self, mock_bpy):
        ops = self._setup()
        result = ops.handle_save_project({"filepath": "output/projects/test"})
        assert result["success"] is True

    def test_handle_restore_checkpoint_accepts_filepath(self, mock_bpy):
        ops = self._setup()
        result = ops.handle_restore_checkpoint({"filepath": "output/checkpoints/test.blend"})
        assert result["success"] is True


# ── Modeling Operator Tests ─────────────────────────────────


class TestModelingOperators:
    def _setup(self):
        import blender_addon.operators.modeling as ops
        importlib.reload(ops)
        ops.register()
        return ops

    def test_handle_add_modifier_valid(self, mock_bpy):
        from tests.conftest import MockBlenderObject
        obj = MockBlenderObject("ModMesh")
        mock_bpy._test_register_object(obj)

        ops = self._setup()
        result = ops.handle_add_modifier({
            "object_name": "ModMesh",
            "modifier_type": "bevel",
        })
        assert result["success"] is True

    def test_handle_add_modifier_bad_type(self, mock_bpy):
        from tests.conftest import MockBlenderObject
        obj = MockBlenderObject("ModMesh2")
        mock_bpy._test_register_object(obj)

        ops = self._setup()
        with pytest.raises(ValueError, match="Unsupported"):
            ops.handle_add_modifier({
                "object_name": "ModMesh2",
                "modifier_type": "warp_drive",
            })


# ── Validation Operator Tests ───────────────────────────────


class TestValidationOperators:
    def _setup(self):
        import blender_addon.operators.validation as ops
        importlib.reload(ops)
        ops.register()
        return ops

    def test_handle_check_transforms_valid(self, mock_bpy):
        from tests.conftest import MockBlenderObject
        obj = MockBlenderObject("ValObj")
        mock_bpy._test_register_object(obj)

        ops = self._setup()
        result = ops.handle_check_transforms({"name": "ValObj"})
        assert result["passed"] is True

    def test_handle_validate_asset_empty_name(self, mock_bpy):
        ops = self._setup()
        with pytest.raises(ValueError, match="name cannot be empty"):
            ops.handle_validate_asset({"name": ""})
