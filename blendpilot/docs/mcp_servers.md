# `mcp_servers/` — Model Context Protocol Servers

> **Phase**: 3 (⬜ Pending)
> **Dependencies**: `mcp-python-sdk`, `blender_addon/bridge.py`, `core/`
> **Consumed by**: `agents/` via LangChain MCP tool wrappers

---

## Purpose

The MCP (Model Context Protocol) layer exposes Blender operations as **standardized tools** that LLMs can discover, understand, and invoke. MCP provides:

- A protocol for tool discovery (tool name, description, input schema)
- Structured tool invocation with validated inputs
- Standardized error handling
- Tool result formatting for LLM consumption

This layer sits between the AI agents and the Blender bridge.

---

## Directory Structure

```
mcp_servers/
├── __init__.py
└── blender/
    ├── __init__.py
    ├── server.py           # MCP server implementation
    └── tools/
        ├── __init__.py
        ├── scene_tools.py       # get_scene_summary, get_object_details, get_mesh_statistics
        ├── object_tools.py      # create_primitive, set_transform, duplicate, delete
        ├── modeling_tools.py    # add_modifier, apply_modifier, edit_mesh
        ├── material_tools.py   # create_material, assign_material
        ├── qa_tools.py          # validate_asset, check_normals, check_triangle_count
        ├── render_tools.py      # setup_camera, setup_lighting, render_preview
        └── project_tools.py     # save_checkpoint, restore_checkpoint, export_asset
```

---

## Implementation Plan (Phase 3)

### Step 1: MCP Server (`server.py`)

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("blendpilot-blender")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="create_primitive",
            description="Create a Blender mesh primitive (cube, sphere, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "primitive_type": {"type": "string", "enum": ["cube","sphere","cylinder","plane","cone","torus"]},
                    "name": {"type": "string"},
                    "dimensions": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                    "location": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                },
                "required": ["primitive_type", "name"],
            },
        ),
        # ... all other tools
    ]
```

### Step 2: Tool Implementations

Each tool function:
1. Receives validated parameters from MCP
2. Sends a command to the Blender bridge (HTTP POST to localhost:9876)
3. Receives the bridge response
4. Formats it as MCP `TextContent` for the LLM

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handler = TOOL_REGISTRY.get(name)
    if not handler:
        raise ToolError(f"Unknown tool: {name}")

    result = await handler(arguments)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
```

### Step 3: Initial Tool Set (MVP)

Only implement these tools first:

| Category | Tools |
|----------|-------|
| **Scene** | `get_scene_summary` |
| **Objects** | `create_primitive`, `set_transform` |
| **Modeling** | `add_modifier` |
| **Materials** | `create_material` |
| **Rendering** | `render_preview` |
| **Project** | `save_project` |

Expand after MVP is validated.

---

## MCP Server Configuration

```json
{
    "mcpServers": {
        "blendpilot-blender": {
            "command": "python",
            "args": ["-m", "mcp_servers.blender.server"],
            "env": {
                "BLENDER_BRIDGE_HOST": "127.0.0.1",
                "BLENDER_BRIDGE_PORT": "9876"
            }
        }
    }
}
```

---

## Future MCP Servers

| Server | Phase | Purpose |
|--------|-------|---------|
| `blender/` | 3 | Blender operations via bridge |
| `email/` | 9 | Email review workflow |
| `filesystem/` | 3 | File read/write for project management |
