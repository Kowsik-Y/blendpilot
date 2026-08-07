"""
BlendPilot AI — Blender Bridge Client

HTTP client for communicating with the Blender add-on bridge server.
Sends structured commands and receives validated responses.

Phase: 2 (interface defined, implementation pending)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("blendpilot.services.blender_client")


# ── Request / Response Models ───────────────────────────────


class BridgeCommand(BaseModel):
    """Command sent to the Blender bridge server."""

    command: str = Field(..., description="Command name, e.g. 'create_primitive'")
    request_id: str = Field(
        default_factory=lambda: f"req_{uuid.uuid4().hex[:8]}",
        description="Unique request identifier for tracking",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Command-specific parameters",
    )


class BridgeResponse(BaseModel):
    """Response received from the Blender bridge server."""

    request_id: str
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    execution_time_ms: float = 0.0


# ── Client ──────────────────────────────────────────────────


class BlenderClient:
    """Async HTTP client for the Blender bridge server.

    Sends JSON commands to the bridge and returns structured responses.
    All commands are validated before sending.

    Usage:
        client = BlenderClient(host="127.0.0.1", port=9876)
        result = await client.create_primitive(
            primitive_type="cube",
            name="MyCube",
            dimensions=[1.0, 1.0, 1.0],
        )
        await client.close()
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9876,
        timeout: float = 30.0,
    ):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self._client = None  # httpx.AsyncClient — created on first use

    async def _get_client(self):
        """Lazy-initialize the HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def execute(self, command: str, parameters: dict[str, Any] | None = None) -> BridgeResponse:
        """Send a command to the Blender bridge.

        Args:
            command: Command name (must be registered on the bridge).
            parameters: Command-specific parameters.

        Returns:
            BridgeResponse with success status and result data.

        Raises:
            ConnectionError: If the bridge is not reachable.
            httpx.HTTPStatusError: If the bridge returns an error status.
        """
        req = BridgeCommand(command=command, parameters=parameters or {})
        logger.info("Sending command: %s (id=%s)", command, req.request_id)

        client = await self._get_client()
        response = await client.post("/execute", json=req.model_dump())
        response.raise_for_status()

        result = BridgeResponse.model_validate(response.json())
        logger.info(
            "Response for %s: success=%s (%.1fms)",
            req.request_id, result.success, result.execution_time_ms,
        )
        return result

    # ── Convenience Methods ─────────────────────────────────

    async def create_primitive(self, **kwargs) -> BridgeResponse:
        """Create a mesh primitive in Blender."""
        return await self.execute("create_primitive", kwargs)

    async def set_transform(self, **kwargs) -> BridgeResponse:
        """Set the transform of an object."""
        return await self.execute("set_transform", kwargs)

    async def duplicate_object(self, **kwargs) -> BridgeResponse:
        """Duplicate an object."""
        return await self.execute("duplicate_object", kwargs)

    async def delete_object(self, name: str) -> BridgeResponse:
        """Delete an object by name."""
        return await self.execute("delete_object", {"name": name})

    async def add_modifier(self, **kwargs) -> BridgeResponse:
        """Add a modifier to an object."""
        return await self.execute("add_modifier", kwargs)

    async def apply_modifier(self, **kwargs) -> BridgeResponse:
        """Apply a modifier to an object's mesh."""
        return await self.execute("apply_modifier", kwargs)

    async def create_material(self, **kwargs) -> BridgeResponse:
        """Create a Principled BSDF material."""
        return await self.execute("create_material", kwargs)

    async def assign_material(self, **kwargs) -> BridgeResponse:
        """Assign a material to an object."""
        return await self.execute("assign_material", kwargs)

    async def get_scene_summary(self) -> BridgeResponse:
        """Get a structured summary of the current scene."""
        return await self.execute("get_scene_summary")

    async def get_object_details(self, name: str) -> BridgeResponse:
        """Get detailed info for a specific object."""
        return await self.execute("get_object_details", {"name": name})

    async def get_mesh_statistics(self, name: str) -> BridgeResponse:
        """Get mesh statistics for an object."""
        return await self.execute("get_mesh_statistics", {"name": name})

    async def validate_asset(self, **kwargs) -> BridgeResponse:
        """Run geometry QA validation."""
        return await self.execute("validate_asset", kwargs)

    async def setup_preview_camera(self, **kwargs) -> BridgeResponse:
        """Set up a preview camera."""
        return await self.execute("setup_preview_camera", kwargs)

    async def setup_studio_lighting(self, **kwargs) -> BridgeResponse:
        """Set up studio lighting."""
        return await self.execute("setup_studio_lighting", kwargs)

    async def render_preview(self, output_path: str, **kwargs) -> BridgeResponse:
        """Render a preview image."""
        return await self.execute("render_preview", {"output_path": output_path, **kwargs})

    async def save_checkpoint(self, path: str) -> BridgeResponse:
        """Save a project checkpoint."""
        return await self.execute("save_checkpoint", {"path": path})

    async def restore_checkpoint(self, path: str) -> BridgeResponse:
        """Restore a project checkpoint."""
        return await self.execute("restore_checkpoint", {"path": path})

    async def save_project(self, path: str) -> BridgeResponse:
        """Save the current project."""
        return await self.execute("save_project", {"path": path})

    async def export_asset(self, **kwargs) -> BridgeResponse:
        """Export objects as FBX or GLB."""
        return await self.execute("export_asset", kwargs)

    # ── Connection Management ───────────────────────────────

    async def health_check(self) -> bool:
        """Check if the Blender bridge is running and reachable."""
        try:
            client = await self._get_client()
            resp = await client.get("/health")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Close the HTTP client connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Blender client connection closed.")
