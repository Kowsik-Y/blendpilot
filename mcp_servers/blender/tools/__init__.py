"""
BlendPilot AI — Blender MCP Tools Registry
"""

from mcp_servers.blender.tools.materials import assign_material, create_material
from mcp_servers.blender.tools.modeling import add_modifier, apply_modifier, edit_mesh
from mcp_servers.blender.tools.objects import (
    create_primitive,
    delete_object,
    duplicate_object,
    set_transform,
)
from mcp_servers.blender.tools.project import (
    export_asset,
    restore_checkpoint,
    save_checkpoint,
    save_project,
)
from mcp_servers.blender.tools.rendering import (
    render_preview,
    setup_preview_camera,
    setup_studio_lighting,
)
from mcp_servers.blender.tools.scene import (
    get_mesh_statistics,
    get_object_details,
    get_scene_summary,
)
from mcp_servers.blender.tools.validation import (
    check_non_manifold,
    check_normals,
    check_triangle_count,
    validate_asset,
)

__all__ = [
    # Scene
    "get_scene_summary",
    "get_object_details",
    "get_mesh_statistics",
    # Objects
    "create_primitive",
    "set_transform",
    "duplicate_object",
    "delete_object",
    # Modeling
    "add_modifier",
    "apply_modifier",
    "edit_mesh",
    # Materials
    "create_material",
    "assign_material",
    # Validation
    "validate_asset",
    "check_non_manifold",
    "check_normals",
    "check_triangle_count",
    # Rendering
    "setup_preview_camera",
    "setup_studio_lighting",
    "render_preview",
    # Project
    "save_checkpoint",
    "restore_checkpoint",
    "save_project",
    "export_asset",
]
