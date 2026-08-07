# `tests/` — Test Suite

> **Phase**: 1 (✅ Complete for Phase 1)
> **Dependencies**: `pytest`, `pytest-cov`
> **Tests**: 92 passing

---

## Purpose

Comprehensive test suite that runs **outside Blender** using a mock `bpy` module. Tests cover:

- Input validation (empty names, invalid types, out-of-range values)
- Error handling (object not found, type mismatches)
- Schema validation (Pydantic models, JSON roundtrips)
- Business logic (plan completion tracking, severity counting)

---

## Test Inventory

| File | Tests | Module Under Test |
|------|-------|-------------------|
| `test_schemas.py` | 24 | All Pydantic models (design, scene, plan, validation) |
| `test_objects.py` | 15 | `core/objects.py` — CRUD input validation |
| `test_modifiers.py` | 11 | `core/modifiers.py` — modifier type & param validation |
| `test_materials.py` | 14 | `core/materials.py` — color, metallic, emission validation |
| `test_scene.py` | 5 | `core/scene.py` — query input validation |
| `test_validation.py` | 10 | `core/validation.py` — geometry QA input validation |
| `test_project.py` | 8 | `core/project.py` — save/export input validation |
| **Total** | **92** | |

---

## Mock System (`conftest.py`)

The `conftest.py` provides a comprehensive mock environment:

| Mock | What It Simulates |
|------|-------------------|
| `MockBlenderObject` | `bpy.data.objects[name]` — name, type, transform, modifiers, materials |
| `MockModifierCollection` | `obj.modifiers` — new, get, iterate |
| `MockMeshData` | `obj.data` — vertices, edges, polygons, UV layers |
| `MockMaterialList` | `obj.data.materials` — append, iterate |
| `MockNodeCollection` | `mat.node_tree.nodes` — Principled BSDF, Output Material |
| `MockVector` | `mathutils.Vector` — basic vector math, `to_track_quat` |
| `create_mock_bpy()` | Full `bpy` module with data, context, ops |

The `mock_bpy` fixture is **autouse** — it injects automatically into every test.

---

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific file
python -m pytest tests/test_schemas.py -v

# With coverage
python -m pytest tests/ --cov=core --cov=schemas --cov-report=term-missing
```

---

## Future Test Expansion

| Phase | Tests to Add |
|-------|-------------|
| 2 | Bridge server request/response handling |
| 3 | MCP tool registration and invocation |
| 4 | LangGraph state transitions, node execution |
| 5 | Geometry QA repair loop (mock repair → revalidate) |
| 6 | Visual critique mock (fake render → parse feedback) |
| 10 | End-to-end integration tests with benchmark prompts |
