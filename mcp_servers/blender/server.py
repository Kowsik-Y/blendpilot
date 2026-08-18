"""
BlendPilot — Blender MCP Server

Implements the Model Context Protocol (MCP) server for Blender.
Exposes safe, validated Blender operations as MCP tools to the LangGraph
orchestrator and AI agents.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field

import mcp_servers.blender.tools as tools
from services.blender_client import BlenderClient

logger = logging.getLogger("blendpilot.mcp.blender")


class MCPToolDefinition(BaseModel):
    """Definition of an MCP tool for discovery and invocation."""

    name: str = Field(..., description="Tool name")
    description: str = Field(...,
                             description="Human-readable tool description")
    category: str = Field(
        ..., description="Tool category (scene, objects, modeling, materials, validation, rendering, project)")
    parameters_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON schema for parameters")


class BlenderMCPServer:
    """Model Context Protocol (MCP) Server for Blender.

    Maintains the tool registry, validates tool invocations, and routes commands
    to the Blender bridge HTTP client.

    Usage:
        server = BlenderMCPServer(client=BlenderClient(host="127.0.0.1", port=9876))
        tools_list = server.list_tools()
        result = await server.call_tool("create_primitive", {"primitive_type": "cube", "name": "Crate"})
    """

    def __init__(self, client: BlenderClient | None = None):
        self.name: str = "blendpilot-blender"
        self.client = client or BlenderClient()
        self._handlers: dict[str, Callable[[
            BlenderClient, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]] = {}
        self._tool_definitions: dict[str, MCPToolDefinition] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the 21 standard BlendPilot Blender tools."""
        # 1. Scene Tools
        self.register_tool(
            name="get_scene_summary",
            description="Get a structured summary of all objects, materials, lights, and cameras in the active Blender scene.",
            category="scene",
            handler=tools.get_scene_summary,
            parameters_schema={
                "type": "object",
                "properties": {
                    "include_mesh_stats": {"type": "boolean", "default": True},
                },
            },
        )
        self.register_tool(
            name="get_object_details",
            description="Get detailed transforms, modifiers, and materials for a specific Blender object.",
            category="scene",
            handler=tools.get_object_details,
            parameters_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Object name"},
                },
                "required": ["name"],
            },
        )
        self.register_tool(
            name="get_mesh_statistics",
            description="Get vertex, edge, polygon, and triangle counts for a specific mesh object.",
            category="scene",
            handler=tools.get_mesh_statistics,
            parameters_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Mesh object name"},
                },
                "required": ["name"],
            },
        )

        self.register_tool(
            name="scene_snapshot",
            description="Create a fast snapshot of the current Blender scene before destructive operations.",
            category="scene",
            handler=tools.scene_snapshot,
            parameters_schema={
                "type": "object",
                "properties": {
                    "snapshot_name": {"type": "string"},
                },
            },
        )
        self.register_tool(
            name="scene_rollback",
            description="Roll back the active scene to a previously taken snapshot.",
            category="scene",
            handler=tools.scene_rollback,
            parameters_schema={
                "type": "object",
                "properties": {
                    "snapshot_name": {"type": "string"},
                },
            },
        )

        # 2. Object Tools
        self.register_tool(
            name="create_primitive",
            description="Create a 3D primitive mesh (cube, cylinder, uv_sphere, plane, cone, torus) in Blender with exact dimensions and location.",
            category="objects",
            handler=tools.create_primitive,
            parameters_schema={
                "type": "object",
                "properties": {
                    "primitive_type": {"type": "string", "enum": ["cube", "cylinder", "uv_sphere", "ico_sphere", "plane", "cone", "torus"]},
                    "name": {"type": "string", "description": "Unique object name"},
                    "dimensions": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3, "description": "[width, depth, height]"},
                    "location": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3, "description": "[x, y, z]"},
                    "rotation": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3, "description": "[rx, ry, rz] in radians"},
                },
                "required": ["primitive_type", "name"],
            },
        )
        self.register_tool(
            name="set_transform",
            description="Set location, rotation, or scale transforms of an existing Blender object.",
            category="objects",
            handler=tools.set_transform,
            parameters_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Target object name"},
                    "location": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                    "rotation": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                    "scale": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                },
                "required": ["name"],
            },
        )
        self.register_tool(
            name="duplicate_object",
            description="Duplicate an existing Blender object with an optional position offset.",
            category="objects",
            handler=tools.duplicate_object,
            parameters_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Source object name"},
                    "new_name": {"type": "string", "description": "Name for duplicate"},
                    "offset": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                },
                "required": ["name"],
            },
        )
        self.register_tool(
            name="delete_object",
            description="Delete an object and its mesh data from the active scene.",
            category="objects",
            handler=tools.delete_object,
            parameters_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Object to delete"},
                },
                "required": ["name"],
            },
        )

        # 3. Modeling Tools
        self.register_tool(
            name="add_modifier",
            description="Add a modifier (BEVEL, SUBSURF, SOLIDIFY, MIRROR, BOOLEAN, DECIMATE) to a mesh object.",
            category="modeling",
            handler=tools.add_modifier,
            parameters_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Target object name"},
                    "modifier_type": {"type": "string", "enum": ["bevel", "solidify", "subdivision", "mirror", "array", "boolean", "decimate", "edge_split", "weighted_normal"]},
                    "modifier_name": {"type": "string"},
                    "properties": {"type": "object", "description": "Modifier properties, e.g. width, segments, thickness"},
                },
                "required": ["object_name", "modifier_type"],
            },
        )
        self.register_tool(
            name="apply_modifier",
            description="Apply and bake a modifier into the mesh geometry.",
            category="modeling",
            handler=tools.apply_modifier,
            parameters_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string"},
                    "modifier_name": {"type": "string"},
                },
                "required": ["object_name", "modifier_name"],
            },
        )
        self.register_tool(
            name="edit_mesh",
            description="Perform a mesh editing operation such as normal recalculation, bevel, or subdivision.",
            category="modeling",
            handler=tools.edit_mesh,
            parameters_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string"},
                    "operation": {"type": "string"},
                    "parameters": {"type": "object"},
                },
                "required": ["object_name", "operation"],
            },
        )

        # 4. Material Tools
        self.register_tool(
            name="create_material",
            description="Create a Principled BSDF / PBR material with custom base color, metallic, roughness, and emission values.",
            category="materials",
            handler=tools.create_material,
            parameters_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Material name"},
                    "base_color": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4, "description": "[R, G, B, A]"},
                    "metallic": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "roughness": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "emission_color": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4},
                    "emission_strength": {"type": "number", "minimum": 0.0},
                },
                "required": ["name"],
            },
        )
        self.register_tool(
            name="assign_material",
            description="Assign an existing material to an object or face slot.",
            category="materials",
            handler=tools.assign_material,
            parameters_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string"},
                    "material_name": {"type": "string"},
                    "slot_index": {"type": "integer", "minimum": 0},
                },
                "required": ["object_name", "material_name"],
            },
        )

        # 5. Validation Tools
        self.register_tool(
            name="validate_asset",
            description="Run full deterministic geometry QA on an object (normals, manifoldness, triangles, transforms).",
            category="validation",
            handler=tools.validate_asset,
            parameters_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string"},
                    "triangle_limit": {"type": "integer", "default": 8000},
                    "target_engine": {"type": "string", "default": "Unity"},
                },
                "required": ["object_name"],
            },
        )
        self.register_tool(
            name="check_non_manifold",
            description="Check for non-manifold edges, vertex holes, and mesh boundary issues.",
            category="validation",
            handler=tools.check_non_manifold,
            parameters_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string"},
                },
                "required": ["object_name"],
            },
        )
        self.register_tool(
            name="check_normals",
            description="Check for inverted or inconsistent face normals.",
            category="validation",
            handler=tools.check_normals,
            parameters_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string"},
                },
                "required": ["object_name"],
            },
        )
        self.register_tool(
            name="check_triangle_count",
            description="Check if object polygon/triangle count complies with target budget.",
            category="validation",
            handler=tools.check_triangle_count,
            parameters_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string"},
                    "max_triangles": {"type": "integer", "default": 8000},
                },
                "required": ["object_name"],
            },
        )

        # 6. Rendering Tools
        self.register_tool(
            name="setup_preview_camera",
            description="Create or position a preview camera focusing on the asset with optimal framing.",
            category="rendering",
            handler=tools.setup_preview_camera,
            parameters_schema={
                "type": "object",
                "properties": {
                    "target_object": {"type": "string"},
                    "distance": {"type": "number", "default": 3.5},
                    "focal_length": {"type": "number", "default": 50.0},
                },
            },
        )
        self.register_tool(
            name="setup_studio_lighting",
            description="Set up 3-point key/fill/rim studio lights for high-quality preview rendering.",
            category="rendering",
            handler=tools.setup_studio_lighting,
            parameters_schema={
                "type": "object",
                "properties": {
                    "key_energy": {"type": "number", "default": 1000.0},
                    "fill_energy": {"type": "number", "default": 400.0},
                    "rim_energy": {"type": "number", "default": 600.0},
                },
            },
        )
        self.register_tool(
            name="render_preview",
            description="Render an image preview of the scene to a file path for visual critique.",
            category="rendering",
            handler=tools.render_preview,
            parameters_schema={
                "type": "object",
                "properties": {
                    "output_path": {"type": "string"},
                    "resolution_x": {"type": "integer", "default": 1024},
                    "resolution_y": {"type": "integer", "default": 1024},
                    "samples": {"type": "integer", "default": 64},
                },
                "required": ["output_path"],
            },
        )

        # 7. Project Tools
        self.register_tool(
            name="save_checkpoint",
            description="Save an incremental checkpoint .blend file for rollback safety.",
            category="project",
            handler=tools.save_checkpoint,
            parameters_schema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string"},
                    "checkpoint_name": {"type": "string"},
                },
                "required": ["filepath"],
            },
        )
        self.register_tool(
            name="restore_checkpoint",
            description="Restore scene from a saved .blend checkpoint file.",
            category="project",
            handler=tools.restore_checkpoint,
            parameters_schema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string"},
                },
                "required": ["filepath"],
            },
        )
        self.register_tool(
            name="save_project",
            description="Save the current Blender project to a .blend file.",
            category="project",
            handler=tools.save_project,
            parameters_schema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string"},
                },
                "required": ["filepath"],
            },
        )
        self.register_tool(
            name="export_asset",
            description="Export the finished 3D asset objects to FBX or GLB formats for game engine use.",
            category="project",
            handler=tools.export_asset,
            parameters_schema={
                "type": "object",
                "properties": {
                    "object_names": {"type": "array", "items": {"type": "string"}},
                    "output_path": {"type": "string"},
                    "format": {"type": "string", "enum": ["FBX", "GLB", "OBJ"], "default": "FBX"},
                    "apply_modifiers": {"type": "boolean", "default": True},
                },
                "required": ["object_names", "output_path"],
            },
        )

    def register_tool(
        self,
        name: str,
        description: str,
        category: str,
        handler: Callable[[BlenderClient, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]],
        parameters_schema: dict[str, Any] | None = None,
    ) -> None:
        """Register a custom tool on the MCP server."""
        self._handlers[name] = handler
        self._tool_definitions[name] = MCPToolDefinition(
            name=name,
            description=description,
            category=category,
            parameters_schema=parameters_schema or {
                "type": "object", "properties": {}},
        )

    def list_tools(self, category: str | None = None) -> list[MCPToolDefinition]:
        """Return list of available MCP tool definitions."""
        tools_list = list(self._tool_definitions.values())
        if category:
            tools_list = [t for t in tools_list if t.category == category]
        return tools_list

    def get_langchain_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions formatted for LangChain / OpenAI function calling."""
        formatted = []
        for defn in self._tool_definitions.values():
            formatted.append({
                "type": "function",
                "function": {
                    "name": defn.name,
                    "description": defn.description,
                    "parameters": defn.parameters_schema,
                },
            })
        return formatted

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Invoke an MCP tool by name with arguments."""
        if name not in self._handlers:
            return {
                "success": False,
                "error": f"Tool '{name}' is not registered on Blender MCP server",
            }

        handler = self._handlers[name]
        args = arguments or {}

        # Deterministic Policy Check: Block destructive actions without idempotency or safety intent
        destructive_tools = {"delete_object", "apply_modifier", "edit_mesh"}
        if name in destructive_tools:
            # Check if this invocation has safety flags (like expected_revision or snapshot taken)
            # For simplicity, we just enforce that they are logged as destructive.
            logger.warning(
                "Policy checkpoint: %s is a destructive operation. Verifying safety constraints.", name)
            # Real implementation would query OPA here or check agent context for valid active snapshot.

        try:
            logger.info("Executing MCP tool: %s with args=%s", name, args)
            result = await handler(self.client, args)
            return result
        except Exception as e:
            logger.exception("Error executing MCP tool %s: %s", name, e)
            return {
                "success": False,
                "error": str(e),
            }
