# Model Context Protocol (MCP) Servers

BlendPilot utilizes the **Model Context Protocol (MCP)** to provide a standardized, secure boundary between the Large Language Models (LLMs) and the Blender `bpy` executable environment.

## Why MCP?

Allowing LLMs to directly write and execute raw Python scripts inside Blender (`bpy`) is highly unstable. It frequently leads to syntax errors, unsupported API calls (which change across Blender versions), and context crashes.

MCP solves this by exposing predefined **tools** and **resources** rather than arbitrary code execution. 

## Blender MCP Server

The Blender MCP Server (`mcp_servers/blender/`) defines explicit tools the agents can call:

### Available Tools

1. **`add_primitive`**: Adds basic meshes (cube, cylinder, sphere) with specific dimensions and locations.
2. **`apply_modifier`**: Adds safe modifiers (Subdivision, Bevel, Boolean, Mirror) with bounded parameters.
3. **`edit_mesh`**: Executes deterministic mesh transformations (extrude, inset, scale) via bmesh.
4. **`assign_material`**: Creates node-based Principled BSDF materials and assigns them to object slots.
5. **`render_preview`**: Triggers a Cycles/Eevee render and returns the filepath to the visual critic agent.

### Protocol Flow

1. The **ModelingAgent** decides to add a base mesh.
2. It calls the MCP tool `add_primitive(type="CUBE", scale=[1, 2, 1])`.
3. The MCP Server validates the JSON schema of the tool call.
4. The MCP Server translates this into `bpy.ops.mesh.primitive_cube_add()` and executes it inside Blender.
5. The Server returns a success state or a detailed error trace back to the agent.

This architecture ensures the agents can never crash the host application with syntax errors, providing the stability required for a 10-agent pipeline.
