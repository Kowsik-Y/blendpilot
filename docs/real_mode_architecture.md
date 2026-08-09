# BlendPilot — Simulation vs. Real Mode Architecture

> **Investigation only — no code was modified.**

---

## 1. Overview

BlendPilot has two distinct execution modes. They are **not configured by an env var**.  
They are detected **at runtime** by whether `import bpy` succeeds.

```
bpy importable?
├─ YES  → real mode  (code runs inside Blender's Python interpreter)
└─ NO   → simulation mode  (code runs in external Python / FastAPI process)
```

---

## 2. Simulation Mode — What Happens

### Detection Point

Every node and agent that touches Blender hardware uses the same idiom:

```python
# graph/nodes.py — node_executor(), node_render(), node_repair(), node_refinement()
try:
    import bpy
    mock_mode = False
except ImportError:
    mock_mode = True   # ← always True when FastAPI is the host process
```

### What `mock_mode = True` does

| Component | Simulation behaviour | File |
|---|---|---|
| **GenerationAgent** | All plan steps return `{"mocked": True, success: True}`. No object is actually created. `created_objects` is populated only from operations named `create_primitive` / `duplicate_object` (using `step.target` as the name). | `agents/generation_agent.py:102-106` |
| **BlenderClient.execute()** | First tries `POST http://127.0.0.1:9876/execute` (live bridge). On any `Exception` (e.g. `ConnectionRefused`), falls through to `_simulate_command()`. | `services/blender_client.py:87-102` |
| **BlenderClient._simulate_command()** | Maintains an in-memory `_mock_objects` dict. Returns hardcoded `success=True` responses. `get_scene_summary` returns objects from that dict. `validate_asset` always returns `"status": "PASS"` with `triangle_count=240`. `render_preview` returns `{"rendered": True}` without writing any file. | `services/blender_client.py:104-278` |
| **node_render** | Detects `mock_mode` and logs `"Mock mode: skipping real render."`. Path `output/{obj_type}/preview.png` is computed and stored in state but **no file is written**. | `graph/nodes.py:624-632` |
| **VisionCriticAgent** | If `self.mock_mode` is True **or** `llm_service.config.api_key` is empty string, returns a hardcoded PASS `VisionReport` with `confidence=1.0`. | `agents/vision_critic_agent.py:29-40` |
| **ExportAgent** | `node_export` in `graph/nodes.py:733` logs "Export completed" and immediately returns `COMPLETED`. No MCP tool is called. No file is written. | `graph/nodes.py:727-731` |

### Why `get_scene_summary` returns 0 objects

`node_scene_state` calls `BlenderMCPServer.call_tool("get_scene_summary")`.  
The `BlenderMCPServer` creates a `BlenderClient()` with default `mock_mode=False`.  
`BlenderClient.execute()` tries to connect to `127.0.0.1:9876` (the Blender bridge).  
Since nothing is listening there, it catches the `ConnectionRefused` exception and falls back to `_simulate_command()`.  
`_simulate_command("get_scene_summary")` reads from `self._mock_objects`.  
But **each `BlenderClient` is a new instance** — `self._mock_objects` is **always empty** because the generation steps used a *different* `BlenderClient` instance inside `GenerationAgent`.

**Result: 0 objects returned every time**, causing Geometry QA to find nothing, and the repair loop to run to exhaustion on every generation.

---

## 3. Real Mode — What Should Happen

### Required: Blender Running with the Add-on

Real mode works only when Blender is open and the BlendPilot add-on is enabled. The add-on starts an HTTP bridge server at `127.0.0.1:9876`.

```
FastAPI process (external Python)
    ↓  POST http://127.0.0.1:9876/execute
Blender process (internal Python, has bpy)
    ↓  blender_addon/bridge.py → BridgeRequestHandler
    ↓  blender_addon/operators/*.py → handler function
    ↓  core/*.py (bpy calls live here)
    ↓  Actual Blender scene is modified / rendered / exported
    ←  JSON response { success, result }
FastAPI process
    ← BridgeResponse
```

### What real mode executes

| Bridge Command | Real operator | Core function | Effect |
|---|---|---|---|
| `create_primitive` | `objects.py` | `core.objects.create_primitive()` | `bpy.ops.mesh.primitive_*_add()` — creates a real mesh object |
| `create_material` | `materials.py` | `core.materials.create_material()` | `bpy.data.materials.new()` — real PBR material |
| `assign_material` | `materials.py` | `core.materials.assign_material()` | Assigns material data-block to object |
| `add_modifier` | `objects.py` | `core.objects.add_modifier()` | `bpy.ops.object.modifier_add()` |
| `setup_preview_camera` | `rendering.py` | `core.rendering.setup_preview_camera()` | Creates/moves camera in scene |
| `setup_studio_lighting` | `rendering.py` | `core.rendering.setup_studio_lighting()` | Creates 3 area lights |
| `render_preview` | `rendering.py` | `core.rendering.render_preview()` | `bpy.ops.render.render()` — writes actual `.png` to disk |
| `get_scene_summary` | `rendering.py` | `core.scene.get_scene_summary()` | Reads live `bpy.data.objects` — returns real geometry data |
| `validate_asset` | `validation.py` | `core.validation.validate_asset()` | Checks real mesh topology via `bpy.data.meshes` |
| `export_asset` | `export.py` | `core.project.export_asset()` | `bpy.ops.export_scene.fbx/gltf()` — writes `.fbx` / `.glb` |
| `save_project` | `export.py` | `core.project.save_project()` | `bpy.ops.wm.save_as_mainfile()` — writes `.blend` |

### Vision Critic in real mode

Requires a valid `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`. Uses `LLMService.generate_vision()` with the actual rendered `preview.png` as base64 input. Returns a real `VisionReport` JSON parsed from the LLM response.

---

## 4. Where Each Feature Is Gated

### A. What is preventing real Blender execution?

**Nothing in code prevents it — but the Blender bridge (`127.0.0.1:9876`) is not running.**  
No Blender process is open. No add-on is installed. When `BlenderClient` tries `POST /execute` and gets `ConnectionRefused`, it silently falls back to simulation.

The fallback is the design intention — it allows the agent pipeline to run offline for development. It is not a bug, but it means **all Blender operations are no-ops** when the bridge is absent.

### B. What configuration is required?

No new `.env` variables are needed. The bridge host/port are already in `backend/config.py`:

```
BLENDER_BRIDGE_HOST = 127.0.0.1  (default, not currently consumed by BlenderClient)
BLENDER_BRIDGE_PORT = 9876        (default, hardcoded in BlenderClient __init__)
BLENDER_BRIDGE_TIMEOUT = 30.0    (default, currently 5.0 in BlenderClient)
```

> **Note:** `BlenderClient` currently ignores `backend/config.py` settings — it is always constructed with hardcoded defaults. The `Settings` object is not passed to it.

For Vision Critic:
```
OPENAI_API_KEY=sk-...     # Required for real LLM vision analysis
```
or
```
ANTHROPIC_API_KEY=sk-ant-...  # Alternative provider
```

### C. What code path currently creates mock objects?

```
node_executor()                          graph/nodes.py:386
  └─ GenerationAgent(mock_mode=True)     agents/generation_agent.py:22
       └─ execute() loop                 agents/generation_agent.py:102-106
            └─ mock_mode branch:         "Mock execution of {op} succeeded"
                 created_objects is populated from step.target names only
                 NO BlenderClient calls made
```

When `GenerationAgent` is in mock_mode, it **never calls the MCP server**.  
It just returns success and tracks which operations were named `create_primitive`.

### D. What code path should create real Blender objects?

```
node_executor()                          graph/nodes.py:386
  └─ GenerationAgent(mock_mode=False)    agents/generation_agent.py:22
       └─ _execute_core_operation()      agents/generation_agent.py:152
            └─ core.objects.create_primitive()    core/objects.py
                 └─ bpy.ops.mesh.primitive_cube_add()    [real Blender call]
```

OR via the bridge path (both paths currently lead to the same `core/` functions):

```
node_executor()
  └─ BlenderMCPServer.call_tool("create_primitive")
       └─ BlenderClient.execute("create_primitive")
            └─ POST http://127.0.0.1:9876/execute
                 └─ bridge.py → blender_addon/operators/objects.py
                      └─ core.objects.create_primitive()    [real bpy call]
```

> **Key insight:** `GenerationAgent._execute_core_operation()` calls `core.*` functions **directly**, not through the MCP bridge. This means that even in "real mode" (with `mock_mode=False`), generation runs `core.*` functions which themselves call `bpy` directly. This path only works if `node_executor` is running **inside** Blender — which it never is in the current FastAPI architecture.
>
> **The existing real path for generation is therefore broken** — `mock_mode=False` would crash immediately on `import core.objects` → `import bpy`, not just on `import bpy` in the guard. The `try/except ImportError` on `bpy` at the top of `node_executor` prevents this crash, setting `mock_mode=True` always.
>
> For real execution, generation should route through `BlenderMCPServer.call_tool()` (the bridge), not through direct `core.*` imports.

### E. What is the minimum change required to activate real mode?

1. **Open Blender 4.x** and install the `blender_addon/` folder as an add-on.
2. **Enable the add-on** — this starts the bridge HTTP server at `127.0.0.1:9876`.
3. **Set `.env`:**
   ```
   OPENAI_API_KEY=sk-...    # For intent, planning, vision critique
   ```
4. **No code change is required** for the bridge fallback to activate — `BlenderClient` will detect the bridge is available on `9876` and route all commands through it.
5. **`GenerationAgent` is the exception** — it uses `_execute_core_operation()` with direct `core.*` imports when `mock_mode=False`, which will crash because `bpy` is not available in FastAPI. To use real Blender for generation, `GenerationAgent` must be changed to route through `BlenderMCPServer.call_tool()` instead of calling `core.*` directly.

---

## 5. Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│ SIMULATION MODE (current)                                           │
│                                                                     │
│  FastAPI ─→ LangGraph ─→ node_executor                             │
│                               │                                     │
│                         mock_mode=True                              │
│                          (bpy absent)                               │
│                               │                                     │
│                    GenerationAgent.execute()                        │
│                       ├─ "Mock execution succeeded"                 │
│                       └─ step.target → created_objects[]            │
│                               │                                     │
│               node_scene_state → BlenderClient (new instance)       │
│                    → Connection refused → _simulate_command()        │
│                    → _mock_objects = {} (empty! different instance)  │
│                    → returns 0 objects                              │
│                               │                                     │
│               node_geometry_qa → validate_asset → simulation        │
│                    → always PASS per object (but 0 objects)         │
│                    → missing-object check fails every time          │
│                               │                                     │
│               node_vision_critic → no API key → mock PASS          │
│                               │                                     │
│               node_decision → repairable → repair_node             │
│               (loops 3× to max_iterations → REVIEW_REQUIRED)       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ REAL MODE (requires Blender + add-on + API key)                     │
│                                                                     │
│  FastAPI ─→ LangGraph ─→ node_executor                             │
│                               │                                     │
│                    GenerationAgent(mock_mode=False)                 │
│                               │                                     │
│                    [BROKEN] _execute_core_operation()               │
│                    → imports core.objects (imports bpy) → CRASH     │
│                    OR                                               │
│                    [NEEDED] BlenderMCPServer.call_tool()            │
│                    → BlenderClient.execute()                        │
│                    → POST 127.0.0.1:9876/execute                   │
│                    → Blender bridge receives command                │
│                    → blender_addon/operators/objects.py             │
│                    → core.objects.create_primitive()                │
│                    → bpy.ops.mesh.primitive_cube_add()              │
│                    → Real mesh object created in Blender scene      │
│                               │                                     │
│               node_scene_state → BlenderMCPServer.call_tool()      │
│                    → POST /execute get_scene_summary                │
│                    → blender_addon/operators/rendering.py           │
│                    → core.scene.get_scene_summary()                 │
│                    → bpy.data.objects → real scene data             │
│                               │                                     │
│               node_render → BlenderMCPServer.call_tool()           │
│                    → render_preview → core.rendering.render_preview()│
│                    → bpy.ops.render.render()                        │
│                    → output/table/preview.png written to disk        │
│                               │                                     │
│               node_geometry_qa → validate_asset via bridge          │
│                    → core.validation.validate_asset()               │
│                    → real manifold/normal/triangle checks           │
│                               │                                     │
│               node_vision_critic → LLM reads preview.png           │
│                    → real PASS/FAIL from vision model               │
│                               │                                     │
│               node_export → export_asset via bridge                 │
│                    → core.project.export_asset()                    │
│                    → bpy.ops.export_scene.fbx/gltf()               │
│                    → output/table/table.fbx, table.glb written      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Concrete Answers

| Question | Answer |
|---|---|
| **Where is simulation mode enabled?** | Implicitly — any node that calls `try: import bpy` / `except ImportError: mock_mode = True` |
| **How is simulation mode detected?** | `import bpy` at the top of each node. If it raises `ImportError`, mock_mode is set. |
| **Where does real vs. simulated route?** | `BlenderClient.execute()` — tries bridge on `127.0.0.1:9876`, falls back to `_simulate_command()` on any exception |
| **Where is mock SceneState created?** | `BlenderClient._simulate_command("get_scene_summary")` — returns `self._mock_objects` which is always `{}` because it's a fresh `BlenderClient` instance |
| **Where is preview.png supposed to be generated?** | `node_render()` → `BlenderMCPServer.call_tool("render_preview")` → bridge → `core.rendering.render_preview()` → `bpy.ops.render.render(output_path)` |
| **Where are export files generated?** | `node_export()` → (currently a stub) should call `BlenderMCPServer.call_tool("export_asset")` → bridge → `core.project.export_asset()` → `bpy.ops.export_scene.fbx/gltf()` |
| **Where does Vision Critic switch to mock PASS?** | `agents/vision_critic_agent.py:29` — `if self.mock_mode or not self.llm_service.config.api_key` |
| **Which env vars control these behaviours?** | `OPENAI_API_KEY` (controls Vision Critic and all LLM agents). No env var controls Blender bridge — it is detected by connection success/failure only. |
| **How is Blender executable/path configured?** | Not configured at all. The bridge runs **inside** Blender — FastAPI does not launch Blender as a subprocess. |
| **Can FastAPI invoke Blender?** | No. FastAPI sends HTTP commands to the bridge. The bridge must already be running inside Blender. |
| **How is Blender expected to run?** | As a **Blender Add-on** (`blender_addon/`). User opens Blender manually, installs and enables the add-on. The add-on starts the HTTP bridge at `127.0.0.1:9876`. FastAPI then communicates with it via `BlenderClient`. |

---

## 7. The Shared-State Problem (Root Cause of Repair Loop)

The most impactful simulation bug is not the render — it is the **broken `_mock_objects` state**.

```
node_executor:
    GenerationAgent(mock_mode=True)  # uses its own internal tracking OR
    GenerationAgent(mock_mode=False) # calls core.* directly, crashes avoided by bpy guard
    → Either way, NO shared BlenderClient state is written

node_scene_state:
    BlenderMCPServer() → BlenderClient()   # NEW instance, _mock_objects = {}
    → get_scene_summary returns 0 objects

node_geometry_qa:
    GeometryQAAgent → BlenderMCPServer() → BlenderClient()  # ANOTHER new instance
    → created_objects from state = ["table_base", "leg_1", ...] (from GenerationAgent mock)
    → validates them: validate_asset per object returns PASS (but no geometry check)
    → BUT: missing-object check compares expected_objects vs created_objects
    → expected_objects built from plan.steps parameters
    → created_objects from state = set by executor result
    → Mismatch possible → overall_passed = False
```

**This is why the repair loop fires every time in simulation mode** — the Geometry QA's missing-object check depends on the plan parameters vs. the executor's created_objects list, and in mock mode there may be parameter name vs. target name mismatches.

---

## 8. Minimum Changes to Activate Real Mode

Do not change:
- LangGraph graph structure
- React frontend
- FastAPI API endpoints

Required changes (in priority order):

1. **Install and enable the Blender add-on** — no code change, just Blender UI action
2. **Add `OPENAI_API_KEY` to `.env`** — no code change
3. **Fix `node_render`** — currently a stub that does nothing even in real mode (line 628-632 has a `pass` comment). Must call `BlenderMCPServer.call_tool("render_preview")`.
4. **Fix `node_export`** — currently just logs and returns COMPLETED. Must call `BlenderMCPServer.call_tool("export_asset")` per created object and `BlenderMCPServer.call_tool("save_project")`.
5. **Fix `GenerationAgent` real path** — `_execute_core_operation()` imports `core.*` which requires `bpy`. Should instead call `BlenderMCPServer.call_tool()` so it routes through the bridge even when `mock_mode=False`. This is the key architectural fix for real generation.
