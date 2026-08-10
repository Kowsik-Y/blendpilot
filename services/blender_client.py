"""
BlendPilot AI — Blender Bridge Client

HTTP client for communicating with the Blender add-on bridge server.
Sends structured commands and receives validated responses.
Includes automatic simulation fallback when the bridge is not running.
"""

from __future__ import annotations

import logging
import uuid
import os
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
    If the bridge server is offline (e.g. during local tests), it falls back
    to simulated execution so the agent graph runs seamlessly.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9876,
        timeout: float = 300.0,
        mock_mode: bool = False,
    ):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self.mock_mode = mock_mode
        self._client = None
        self._mock_objects: dict[str, dict[str, Any]] = {}

    async def _get_client(self):
        """Lazy-initialize the HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def execute(self, command: str, parameters: dict[str, Any] | None = None) -> BridgeResponse:
        """Send a command to the Blender bridge with simulated fallback."""
        from backend.config import settings
        req = BridgeCommand(command=command, parameters=parameters or {})

        if not self.mock_mode:
            try:
                client = await self._get_client()
                response = await client.post("/execute", json=req.model_dump())
                if response.status_code == 200:
                    result = BridgeResponse.model_validate(response.json())
                    return result
            except Exception as e:
                logger.error("Real Blender execution failed: bridge is unreachable: %s", e)
                raise RuntimeError(f"Failed to connect to Blender bridge at {self.base_url}/execute. Ensure Blender is running.")
                
            raise RuntimeError(f"Blender bridge returned an error HTTP status.")

        # Simulated fallback execution (only reached if self.mock_mode == True)
        return self._simulate_command(req)

    def _simulate_command(self, req: BridgeCommand) -> BridgeResponse:
        """Simulate Blender command execution for offline / testing environments."""
        cmd = req.command
        params = req.parameters

        if cmd == "create_primitive":
            name = params.get("name", "Object")
            self._mock_objects[name] = {
                "name": name,
                "type": params.get("primitive_type", "cube"),
                "dimensions": params.get("dimensions", [1.0, 1.0, 1.0]),
                "location": params.get("location", [0.0, 0.0, 0.0]),
                "materials": [],
                "modifiers": [],
                "triangle_count": 12,
                "vertex_count": 8,
                "face_count": 6,
            }
            return BridgeResponse(
                request_id=req.request_id,
                success=True,
                result={"name": name, "object_name": name, "triangle_count": 12},
                execution_time_ms=1.2,
            )

        elif cmd == "set_transform":
            name = params.get("name", "")
            if name in self._mock_objects:
                if "location" in params:
                    self._mock_objects[name]["location"] = params["location"]
            return BridgeResponse(
                request_id=req.request_id,
                success=True,
                result={"name": name, "transforms_applied": True},
                execution_time_ms=0.8,
            )

        elif cmd == "duplicate_object":
            source = params.get("name", "")
            new_name = params.get("new_name", f"{source}_copy")
            if source in self._mock_objects:
                self._mock_objects[new_name] = dict(self._mock_objects[source])
                self._mock_objects[new_name]["name"] = new_name
            return BridgeResponse(
                request_id=req.request_id,
                success=True,
                result={"name": new_name, "source": source},
                execution_time_ms=1.5,
            )

        elif cmd == "delete_object":
            name = params.get("name", "")
            self._mock_objects.pop(name, None)
            return BridgeResponse(
                request_id=req.request_id,
                success=True,
                result={"deleted": name},
                execution_time_ms=0.5,
            )

        elif cmd == "add_modifier":
            obj_name = params.get("object_name", "")
            mod_type = params.get("modifier_type", "BEVEL")
            mod_name = params.get("modifier_name", f"{mod_type}_mod")
            if obj_name in self._mock_objects:
                self._mock_objects[obj_name]["modifiers"].append(mod_name)
            return BridgeResponse(
                request_id=req.request_id,
                success=True,
                result={"name": mod_name, "type": mod_type, "object": obj_name},
                execution_time_ms=2.1,
            )

        elif cmd == "apply_modifier":
            obj_name = params.get("object_name", "")
            mod_name = params.get("modifier_name", "")
            return BridgeResponse(
                request_id=req.request_id,
                success=True,
                result={"applied": mod_name, "object": obj_name},
                execution_time_ms=3.0,
            )

        elif cmd == "create_material":
            mat_name = params.get("name", "Material")
            return BridgeResponse(
                request_id=req.request_id,
                success=True,
                result={"name": mat_name, "created": True},
                execution_time_ms=1.1,
            )

        elif cmd == "assign_material":
            obj_name = params.get("object_name", "")
            mat_name = params.get("material_name", "")
            if obj_name in self._mock_objects:
                self._mock_objects[obj_name]["materials"].append(mat_name)
            return BridgeResponse(
                request_id=req.request_id,
                success=True,
                result={"assigned": mat_name, "object": obj_name},
                execution_time_ms=0.9,
            )

        elif cmd == "get_scene_summary":
            objs = []
            for name, obj in self._mock_objects.items():
                objs.append({
                    "name": name,
                    "type": "MESH",
                    "location": obj.get("location", [0.0, 0.0, 0.0]),
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0],
                    "dimensions": obj.get("dimensions", [1.0, 1.0, 1.0]),
                    "materials": obj.get("materials", []),
                    "triangle_count": obj.get("triangle_count", 12),
                    "vertex_count": obj.get("vertex_count", 8),
                    "face_count": obj.get("face_count", 6),
                })
            return BridgeResponse(
                request_id=req.request_id,
                success=True,
                result={
                    "objects": objs,
                    "total_triangles": sum(o.get("triangle_count", 12) for o in objs),
                    "has_camera": True,
                    "has_lights": True,
                    "active_object": list(self._mock_objects.keys())[0] if self._mock_objects else None,
                },
                execution_time_ms=1.8,
            )

        elif cmd == "validate_asset":
            name = params.get("name") or params.get("object_name", "Object")
            tri_limit = params.get("triangle_limit", 10000)
            return BridgeResponse(
                request_id=req.request_id,
                success=True,
                result={
                    "status": "PASS",
                    "object_name": name,
                    "triangle_count": 240,
                    "triangle_limit": tri_limit,
                    "vertex_count": 130,
                    "face_count": 120,
                    "dimensions": [1.0, 0.7, 0.6],
                    "issues": [],
                    "issues_by_severity": {},
                },
                execution_time_ms=2.4,
            )

        elif cmd == "render_preview":
            out_path = params.get("output_path", "output/preview.png")
            return BridgeResponse(
                request_id=req.request_id,
                success=True,
                result={"output_path": out_path, "rendered": True},
                execution_time_ms=15.0,
            )

        elif cmd in ["setup_preview_camera", "setup_studio_lighting", "save_checkpoint", "restore_checkpoint", "save_project", "export_asset", "edit_mesh"]:
            # In mock mode, actually create dummy files to prevent 404s in export
            if cmd in ("save_project", "save_checkpoint"):
                filepath = params.get("filepath", "")
                if filepath:
                    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write("mock_blend_data")
            elif cmd == "export_asset":
                output_path = params.get("output_path", "")
                if output_path:
                    fmt = params.get("format", "FBX")
                    if fmt == "FBX" and not output_path.endswith(".fbx"):
                        output_path += ".fbx"
                    elif fmt in ("GLB", "GLTF") and not output_path.endswith((".glb", ".gltf")):
                        output_path += ".glb"
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write("mock_export_data")
            
            return BridgeResponse(
                request_id=req.request_id,
                success=True,
                result={"command": cmd, "status": "ok", **params},
                execution_time_ms=2.0,
            )

        return BridgeResponse(
            request_id=req.request_id,
            success=True,
            result={"status": "executed", "command": cmd},
            execution_time_ms=1.0,
        )

    # ── Convenience Methods ─────────────────────────────────

    async def create_primitive(self, **kwargs) -> BridgeResponse:
        return await self.execute("create_primitive", kwargs)

    async def set_transform(self, **kwargs) -> BridgeResponse:
        return await self.execute("set_transform", kwargs)

    async def duplicate_object(self, **kwargs) -> BridgeResponse:
        return await self.execute("duplicate_object", kwargs)

    async def delete_object(self, name: str) -> BridgeResponse:
        return await self.execute("delete_object", {"name": name})

    async def add_modifier(self, **kwargs) -> BridgeResponse:
        return await self.execute("add_modifier", kwargs)

    async def apply_modifier(self, **kwargs) -> BridgeResponse:
        return await self.execute("apply_modifier", kwargs)

    async def create_material(self, **kwargs) -> BridgeResponse:
        return await self.execute("create_material", kwargs)

    async def assign_material(self, **kwargs) -> BridgeResponse:
        return await self.execute("assign_material", kwargs)

    async def get_scene_summary(self) -> BridgeResponse:
        return await self.execute("get_scene_summary")

    async def get_object_details(self, name: str) -> BridgeResponse:
        return await self.execute("get_object_details", {"name": name})

    async def get_mesh_statistics(self, name: str) -> BridgeResponse:
        return await self.execute("get_mesh_statistics", {"name": name})

    async def validate_asset(self, **kwargs) -> BridgeResponse:
        return await self.execute("validate_asset", kwargs)

    async def check_non_manifold(self, name: str) -> BridgeResponse:
        return await self.execute("check_non_manifold", {"object_name": name})

    async def check_normals(self, name: str) -> BridgeResponse:
        return await self.execute("check_normals", {"object_name": name})

    async def check_triangle_count(self, **kwargs) -> BridgeResponse:
        return await self.execute("check_triangle_count", kwargs)

    async def render_preview(self, **kwargs) -> BridgeResponse:
        return await self.execute("render_preview", kwargs)

    async def save_checkpoint(self, filepath: str) -> BridgeResponse:
        return await self.execute("save_checkpoint", {"filepath": filepath})

    async def restore_checkpoint(self, filepath: str) -> BridgeResponse:
        return await self.execute("restore_checkpoint", {"filepath": filepath})

    async def save_project(self, filepath: str) -> BridgeResponse:
        return await self.execute("save_project", {"filepath": filepath})

    async def export_asset(self, **kwargs) -> BridgeResponse:
        return await self.execute("export_asset", kwargs)
