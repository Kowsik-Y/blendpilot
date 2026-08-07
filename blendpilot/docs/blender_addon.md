# `blender_addon/` — Blender Add-on & Operators

> **Phase**: 2 (⬜ Pending)
> **Dependencies**: `bpy`, `core/`
> **Consumed by**: `blender_addon/bridge.py` → `mcp_servers/`

---

## Purpose

The Blender add-on is the **execution layer inside Blender**. It:

1. Registers as a Blender add-on (`bl_info`)
2. Runs an HTTP/socket server (the "bridge") that listens for commands
3. Validates incoming command schemas
4. Delegates to `core/` functions for actual Blender operations
5. Returns structured JSON responses

The LLM **never** directly executes arbitrary Python inside Blender. All operations go through validated, controlled operator functions.

---

## Directory Structure

```
blender_addon/
├── __init__.py          # Add-on registration (bl_info, register/unregister)
├── bridge.py            # HTTP/socket server that receives commands
├── schemas.py           # Command/response JSON schemas for the bridge
└── operators/
    ├── __init__.py
    ├── objects.py       # Object CRUD operators (wraps core/objects.py)
    ├── modeling.py      # Modifier & mesh editing operators
    ├── materials.py     # Material creation/assignment operators
    ├── rendering.py     # Camera, lighting, render operators
    ├── validation.py    # Geometry QA operators
    └── export.py        # Save/export operators
```

---

## Implementation Plan (Phase 2)

### Step 1: Bridge Server (`bridge.py`)

Implement a **localhost-only HTTP server** running inside Blender on a configurable port (default: `9876`).

```python
# Command format (incoming JSON):
{
    "command": "create_primitive",
    "request_id": "req_001",
    "parameters": {
        "primitive_type": "cube",
        "name": "CrateBody",
        "dimensions": [1.0, 0.7, 0.6],
        "location": [0, 0, 0.3]
    }
}

# Response format:
{
    "request_id": "req_001",
    "success": true,
    "result": {
        "object_name": "CrateBody"
    },
    "error": null
}
```

**Key design decisions**:
- Use `threading.Thread` for the HTTP server (Blender's main loop is single-threaded)
- Execute Blender operations on the main thread using `bpy.app.timers`
- Bind only to `127.0.0.1` — never expose to network
- Validate every incoming command against `schemas.py` before execution

### Step 2: Command Schemas (`schemas.py`)

Define Pydantic models for every supported command:

```python
class BridgeCommand(BaseModel):
    command: str          # e.g. "create_primitive"
    request_id: str       # unique ID for tracking
    parameters: dict      # command-specific params

class BridgeResponse(BaseModel):
    request_id: str
    success: bool
    result: dict | None
    error: str | None
    execution_time_ms: float
```

### Step 3: Operator Wrappers (`operators/`)

Each operator file wraps the corresponding `core/` module:

```python
# operators/objects.py
from core.objects import create_primitive as _create_primitive

COMMAND_REGISTRY = {
    "create_primitive": handle_create_primitive,
    "set_transform": handle_set_transform,
    "duplicate_object": handle_duplicate_object,
    "delete_object": handle_delete_object,
}

def handle_create_primitive(params: dict) -> dict:
    """Validate params, call core function, return result."""
    # Validate with Pydantic
    validated = CreatePrimitiveParams(**params)
    return _create_primitive(
        primitive_type=validated.primitive_type,
        name=validated.name,
        dimensions=tuple(validated.dimensions) if validated.dimensions else None,
        location=tuple(validated.location),
    )
```

### Step 4: Add-on Registration (`__init__.py`)

```python
bl_info = {
    "name": "BlendPilot AI",
    "blender": (4, 0, 0),
    "category": "3D View",
}

def register():
    from .bridge import start_bridge_server
    start_bridge_server()

def unregister():
    from .bridge import stop_bridge_server
    stop_bridge_server()
```

---

## Acceptance Tests for Phase 2

1. ✅ Install add-on in Blender
2. ✅ Bridge server starts and listens on localhost:9876
3. ✅ External Python can send `create_primitive` command
4. ✅ Cube appears in Blender scene
5. ✅ Invalid commands return structured error responses
6. ✅ Server stops cleanly when add-on is unregistered

---

## Security Constraints

- **Localhost only** — never bind to `0.0.0.0`
- **Command whitelist** — only registered commands are executed
- **No shell access** — no `subprocess`, `os.system`, or `exec`
- **Input validation** — every parameter validated via Pydantic before execution
- **Timeout protection** — commands that hang are terminated after 30 seconds
