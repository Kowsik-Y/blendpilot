"""
BlendPilot AI — Blender MCP Server

Implements the Model Context Protocol (MCP) server for Blender.
Exposes safe, validated Blender operations as MCP tools to the LangGraph
orchestrator and AI agents.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field

import mcp_servers.blender.schemas as schemas
import mcp_servers.blender.tools as tools
from services.blender_client import BlenderClient

logger = logging.getLogger("blendpilot.mcp.blender")


class MCPToolDefinition(BaseModel):
    """Definition of an MCP tool for discovery and invocation."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Human-readable tool description")
    category: str = Field(..., description="Tool category (scene, objects, modeling, materials, validation, rendering, project)")
    input_schema: type[BaseModel] | None = Field(default=None, description="Pydantic class for input validation")
    parameters_schema: dict[str, Any] = Field(default_factory=dict, description="JSON schema for parameters")


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
        self._handlers: dict[str, Callable[[BlenderClient, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]] = {}
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
            input_schema=schemas.GetSceneSummarySchema,
        )
        self.register_tool(
            name="get_object_details",
            description="Get detailed transforms, modifiers, and materials for a specific Blender object.",
            category="scene",
            handler=tools.get_object_details,
            input_schema=schemas.GetObjectDetailsSchema,
        )
        self.register_tool(
            name="get_mesh_statistics",
            description="Get vertex, edge, polygon, and triangle counts for a specific mesh object.",
            category="scene",
            handler=tools.get_mesh_statistics,
            input_schema=schemas.GetMeshStatisticsSchema,
        )

        # 2. Object Tools
        self.register_tool(
            name="create_primitive",
            description="Create a 3D primitive mesh (cube, cylinder, uv_sphere, plane, cone, torus) in Blender with exact dimensions and location.",
            category="objects",
            handler=tools.create_primitive,
            input_schema=schemas.CreatePrimitiveSchema,
        )
        self.register_tool(
            name="set_transform",
            description="Set location, rotation, or scale transforms of an existing Blender object.",
            category="objects",
            handler=tools.set_transform,
            input_schema=schemas.SetTransformSchema,
        )
        self.register_tool(
            name="duplicate_object",
            description="Duplicate an existing Blender object with an optional position offset.",
            category="objects",
            handler=tools.duplicate_object,
            input_schema=schemas.DuplicateObjectSchema,
        )
        self.register_tool(
            name="delete_object",
            description="Delete an object and its mesh data from the active scene.",
            category="objects",
            handler=tools.delete_object,
            input_schema=schemas.DeleteObjectSchema,
        )

        # 3. Modeling Tools
        self.register_tool(
            name="add_modifier",
            description="Add a modifier (BEVEL, SUBSURF, SOLIDIFY, MIRROR, BOOLEAN, DECIMATE) to a mesh object.",
            category="modeling",
            handler=tools.add_modifier,
            input_schema=schemas.AddModifierSchema,
        )
        self.register_tool(
            name="apply_modifier",
            description="Apply and bake a modifier into the mesh geometry.",
            category="modeling",
            handler=tools.apply_modifier,
            input_schema=schemas.ApplyModifierSchema,
        )
        self.register_tool(
            name="edit_mesh",
            description="Perform a mesh editing operation such as normal recalculation, bevel, or subdivision.",
            category="modeling",
            handler=tools.edit_mesh,
            input_schema=schemas.EditMeshSchema,
        )

        # 4. Material Tools
        self.register_tool(
            name="create_material",
            description="Create a Principled BSDF / PBR material with custom base color, metallic, roughness, and emission values.",
            category="materials",
            handler=tools.create_material,
            input_schema=schemas.CreateMaterialSchema,
        )
        self.register_tool(
            name="assign_material",
            description="Assign an existing material to an object or face slot.",
            category="materials",
            handler=tools.assign_material,
            input_schema=schemas.AssignMaterialSchema,
        )

        # 5. Validation Tools
        self.register_tool(
            name="validate_asset",
            description="Run full deterministic geometry QA on an object (normals, manifoldness, triangles, transforms).",
            category="validation",
            handler=tools.validate_asset,
            input_schema=schemas.ValidateAssetSchema,
        )
        self.register_tool(
            name="check_non_manifold",
            description="Check for non-manifold edges, vertex holes, and mesh boundary issues.",
            category="validation",
            handler=tools.check_non_manifold,
            input_schema=schemas.CheckNonManifoldSchema,
        )
        self.register_tool(
            name="check_normals",
            description="Check for inverted or inconsistent face normals.",
            category="validation",
            handler=tools.check_normals,
            input_schema=schemas.CheckNormalsSchema,
        )
        self.register_tool(
            name="check_triangle_count",
            description="Check if object polygon/triangle count complies with target budget.",
            category="validation",
            handler=tools.check_triangle_count,
            input_schema=schemas.CheckTriangleCountSchema,
        )

        # 6. Rendering Tools
        self.register_tool(
            name="setup_preview_camera",
            description="Create or position a preview camera focusing on the asset with optimal framing.",
            category="rendering",
            handler=tools.setup_preview_camera,
            input_schema=schemas.SetupPreviewCameraSchema,
        )
        self.register_tool(
            name="setup_studio_lighting",
            description="Set up 3-point key/fill/rim studio lights for high-quality preview rendering.",
            category="rendering",
            handler=tools.setup_studio_lighting,
            input_schema=schemas.SetupStudioLightingSchema,
        )
        self.register_tool(
            name="render_preview",
            description="Render an image preview of the scene to a file path for visual critique.",
            category="rendering",
            handler=tools.render_preview,
            input_schema=schemas.RenderPreviewSchema,
        )

        # 7. Project Tools
        self.register_tool(
            name="save_checkpoint",
            description="Save an incremental checkpoint .blend file for rollback safety.",
            category="project",
            handler=tools.save_checkpoint,
            input_schema=schemas.SaveCheckpointSchema,
        )
        self.register_tool(
            name="restore_checkpoint",
            description="Restore scene from a saved .blend checkpoint file.",
            category="project",
            handler=tools.restore_checkpoint,
            input_schema=schemas.RestoreCheckpointSchema,
        )
        self.register_tool(
            name="save_project",
            description="Save the current Blender project to a .blend file.",
            category="project",
            handler=tools.save_project,
            input_schema=schemas.SaveProjectSchema,
        )
        self.register_tool(
            name="export_asset",
            description="Export the finished 3D asset objects to FBX or GLB formats for game engine use.",
            category="project",
            handler=tools.export_asset,
            input_schema=schemas.ExportAssetSchema,
        )

    def register_tool(
        self,
        name: str,
        description: str,
        category: str,
        handler: Callable[[BlenderClient, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]],
        input_schema: type[BaseModel] | None = None,
    ) -> None:
        """Register a custom tool on the MCP server."""
        self._handlers[name] = handler
        parameters_schema = input_schema.model_json_schema() if input_schema else {"type": "object", "properties": {}}
        self._tool_definitions[name] = MCPToolDefinition(
            name=name,
            description=description,
            category=category,
            input_schema=input_schema,
            parameters_schema=parameters_schema,
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
        tool_def = self._tool_definitions[name]
        args = arguments or {}
        
        # Validate inputs
        if tool_def.input_schema:
            try:
                from pydantic import ValidationError
                parsed = tool_def.input_schema(**args)
                args = parsed.model_dump(exclude_unset=True)
            except ValidationError as e:
                logger.warning("Validation error for tool %s: %s", name, e)
                return {
                    "success": False,
                    "error": f"Validation Error: {e}",
                }
                
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
