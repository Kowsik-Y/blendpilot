# `core/` — Blender Python Functions

> **Phase**: 1 (✅ Complete)
> **Dependencies**: `bpy`, `bmesh`, `mathutils`
> **Consumed by**: `blender_addon/operators/` (Phase 2), `mcp_servers/blender/tools/` (Phase 3)

---

## Purpose

The `core/` package contains **direct Blender Python API wrappers** — every low-level operation that BlendPilot needs to control Blender. These functions:

- Run **inside Blender's Python environment**
- Validate all inputs before executing
- Return structured `dict` results (success/failure + metadata)
- Log every operation via Python's `logging` module
- Are designed to be consumed by higher-level systems (bridge, MCP, agents)

---

## Module Inventory

| File | Functions | Description |
|------|-----------|-------------|
| `objects.py` | `create_primitive`, `set_transform`, `duplicate_object`, `delete_object` | CRUD operations for Blender objects. Supports 7 primitive types: cube, sphere, cylinder, plane, cone, torus, ico_sphere. |
| `modifiers.py` | `add_modifier`, `apply_modifier` | Add/apply mesh modifiers. Supports 9 types: bevel, solidify, subdivision, mirror, array, boolean, decimate, edge_split, weighted_normal. Each has sensible defaults. |
| `materials.py` | `create_material`, `assign_material` | Create Principled BSDF materials with base color, metallic, roughness, emission. Assign to mesh objects. Reuses existing materials by name. |
| `scene.py` | `get_scene_summary`, `get_object_details`, `get_mesh_statistics` | Read-only scene inspection. `get_mesh_statistics` uses `bmesh` for accurate triangle counting. |
| `rendering.py` | `setup_preview_camera`, `setup_studio_lighting`, `render_preview` | Camera positioning on a sphere, 3-point studio lighting (key/fill/rim), PNG preview rendering with configurable resolution and engine. |
| `validation.py` | `validate_asset`, `check_triangle_count`, `check_normals`, `check_non_manifold`, `check_transforms` | **Deterministic** geometry QA — no LLM involved. Checks triangles, normals, manifold edges, unapplied transforms, missing materials, dimension mismatches. |
| `project.py` | `save_checkpoint`, `restore_checkpoint`, `save_project`, `export_asset` | Project management and export. Supports FBX and GLB formats. Creates directories automatically. |
| `demo.py` | `create_red_table` | End-to-end demo: creates a red table with 4 legs, bevel modifiers, material, camera, lighting, render, save, and export. |

---

## Error Handling Pattern

Every function follows this pattern:

```python
def some_function(name: str, ...) -> dict[str, Any]:
    # 1. Input validation — raise ValueError with descriptive message
    if not name:
        raise ValueError("Object name cannot be empty.")

    # 2. Blender state validation — raise ValueError if preconditions not met
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object '{name}' not found in scene.")

    # 3. Execute operation with logging
    logger.info("Doing something with '%s'", name)
    # ... bpy calls ...

    # 4. Return structured result
    return {"success": True, "message": "...", ...}
```

---

## Return Value Contract

All core functions return a `dict` with at minimum:

| Key | Type | Description |
|-----|------|-------------|
| `success` | `bool` | Whether the operation succeeded |
| `message` | `str` | Human-readable result description |

Additional keys are function-specific (e.g., `object_name`, `material_name`, `triangle_count`).

---

## How Core Functions Connect to Phase 2+

```
Phase 1 (current):     core/objects.py  →  direct bpy calls
Phase 2 (bridge):      blender_addon/operators/objects.py  →  wraps core/objects.py
Phase 3 (MCP):         mcp_servers/blender/tools/  →  exposes as MCP tools
Phase 4 (agents):      agents/modeling_agent.py  →  invokes MCP tools
```
