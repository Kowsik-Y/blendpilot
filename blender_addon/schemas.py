"""
BlendPilot AI — Bridge Command & Response Schemas

Defines the JSON contract between the external BlenderClient
and the Blender add-on bridge server.

Every command is validated against these schemas before execution.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CommandName(str, Enum):
    """All supported bridge commands.

    Each maps to a handler function in the operators/ package.
    """

    # Scene tools
    GET_SCENE_SUMMARY = "get_scene_summary"
    GET_OBJECT_DETAILS = "get_object_details"
    GET_MESH_STATISTICS = "get_mesh_statistics"

    # Object tools
    CREATE_PRIMITIVE = "create_primitive"
    SET_TRANSFORM = "set_transform"
    DUPLICATE_OBJECT = "duplicate_object"
    DELETE_OBJECT = "delete_object"

    # Modeling tools
    ADD_MODIFIER = "add_modifier"
    APPLY_MODIFIER = "apply_modifier"

    # Material tools
    CREATE_MATERIAL = "create_material"
    ASSIGN_MATERIAL = "assign_material"

    # Rendering tools
    SETUP_PREVIEW_CAMERA = "setup_preview_camera"
    SETUP_STUDIO_LIGHTING = "setup_studio_lighting"
    RENDER_PREVIEW = "render_preview"

    # QA tools
    VALIDATE_ASSET = "validate_asset"
    CHECK_TRIANGLE_COUNT = "check_triangle_count"
    CHECK_NORMALS = "check_normals"
    CHECK_NON_MANIFOLD = "check_non_manifold"
    CHECK_TRANSFORMS = "check_transforms"

    # Project tools
    SAVE_CHECKPOINT = "save_checkpoint"
    RESTORE_CHECKPOINT = "restore_checkpoint"
    SAVE_PROJECT = "save_project"
    EXPORT_ASSET = "export_asset"


class BridgeCommand(BaseModel):
    """A command sent to the Blender bridge server.

    Example:
        {
            "command": "create_primitive",
            "request_id": "req_a1b2c3d4",
            "parameters": {
                "primitive_type": "cube",
                "name": "CrateBody",
                "dimensions": [1.0, 0.7, 0.6],
                "location": [0, 0, 0.3]
            }
        }
    """

    command: str = Field(
        ...,
        description="Command name — must match a CommandName enum value",
    )
    request_id: str = Field(
        default_factory=lambda: f"req_{uuid.uuid4().hex[:8]}",
        description="Unique request ID for tracking",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Command-specific parameters",
    )

    def validate_command_name(self) -> bool:
        """Check if the command is in the supported command list."""
        try:
            CommandName(self.command)
            return True
        except ValueError:
            return False


class BridgeResponse(BaseModel):
    """Response returned by the Blender bridge server.

    Example (success):
        {
            "request_id": "req_a1b2c3d4",
            "success": true,
            "result": {"object_name": "CrateBody"},
            "error": null,
            "execution_time_ms": 12.5
        }

    Example (error):
        {
            "request_id": "req_a1b2c3d4",
            "success": false,
            "result": null,
            "error": "Object 'CrateBody' not found in scene.",
            "execution_time_ms": 1.2
        }
    """

    request_id: str
    success: bool = False
    result: dict[str, Any] | None = None
    error: str | None = None
    execution_time_ms: float = 0.0

    @classmethod
    def ok(cls, request_id: str, result: dict[str, Any], elapsed_ms: float = 0.0) -> BridgeResponse:
        """Create a successful response."""
        return cls(
            request_id=request_id,
            success=True,
            result=result,
            execution_time_ms=elapsed_ms,
        )

    @classmethod
    def from_error(cls, request_id: str, message: str, elapsed_ms: float = 0.0) -> BridgeResponse:
        """Create an error response."""
        return cls(
            request_id=request_id,
            success=False,
            error=message,
            execution_time_ms=elapsed_ms,
        )


class HealthResponse(BaseModel):
    """Response from the /health endpoint."""

    status: str = "ok"
    blender_version: str = ""
    addon_version: str = "0.1.0"
    uptime_seconds: float = 0.0
    commands_processed: int = 0


class Timer:
    """Simple context manager for measuring execution time in milliseconds."""

    def __init__(self):
        self.start_time: float = 0.0
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> Timer:
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.elapsed_ms = (time.perf_counter() - self.start_time) * 1000.0
