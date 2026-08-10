# Generator Tool Schema Diagnosis

This document records the root cause investigation of the Generator Agent's invalid tool argument names.

---

## Investigation Date
2026-08-10

---

## Observed Errors (from E2E logs)

```
Validation error for tool create_primitive: 1 validation error for CreatePrimitiveSchema
primitive_type
  Field required [type=missing, input_value={'type': 'cube', 'name': 'table'}, input_type=dict]

Validation error for tool duplicate_object: 1 validation error for DuplicateObjectSchema
name
  Field required [type=missing, input_value={'count': 3, 'object_name': 'leg'}, input_type=dict]

Validation error for tool set_transform: 1 validation error for SetTransformSchema
name
  Field required [type=missing, input_value={'location': [0, 0, 0], 'object_name': 'leg'}, input_type=dict]

Validation error for tool assign_material: 1 validation error for AssignMaterialSchema
material_name
  Field required [type=missing, input_value={'material': 'wood_material', 'object_name': 'table'}, input_type=dict]
```

---

## Full Data Flow Traced

```
PlanningAgent.execute()
    ↓
LLM structured output → ModelingPlan
(ModelingStep.parameters = free dict, no schema enforcement on parameters content)
    ↓
GenerationAgent.translate(plan) → list of serialized steps
    ↓
node_executor → GenerationAgent.execute(spec, plan)
    ↓
_execute_core_operation(step)
    ↓ step.parameters passed directly (with minimal patching)
BlenderMCPServer.call_tool(op, params)
    ↓
Pydantic validation against input_schema (CreatePrimitiveSchema, etc.)
    ↓ FAILS here
```

---

## Canonical Tool Schemas (source of truth)

Located in `mcp_servers/blender/schemas.py`:

| Tool | Required Fields | LLM Produces |
|---|---|---|
| `create_primitive` | `primitive_type`, `name` | `type` instead of `primitive_type` |
| `set_transform` | `name` | `object_name` instead of `name` |
| `duplicate_object` | `name` | `object_name` instead of `name` |
| `delete_object` | `name` | `object_name` instead of `name` |
| `assign_material` | `object_name`, `material_name` | `material` instead of `material_name` |
| `add_modifier` | `object_name`, `modifier_type` | ✅ correct |
| `create_material` | `name` | ✅ correct |
| `save_checkpoint` | `filepath` | missing `filepath` entirely |
| `save_project` | `filepath` | missing `filepath` entirely |

---

## Root Cause

**Root Cause A: Planning Agent LLM prompt** — The LLM that generates `ModelingPlan` steps uses generic field names in `parameters` (e.g. `type`, `object_name`, `name`, `material`) that differ from the canonical MCP schema field names.

The `ModelingPlan.steps[].parameters` is a free `dict[str, Any]` — Pydantic does not validate what is inside it. So incorrect field names pass through silently until reaching the MCP schema validation.

**Root Cause B: `_execute_core_operation` only partially normalizes**  
In `generation_agent.py`, the `_execute_core_operation` method only performs partial normalization:
- It injects `name = step.target` if `name` not in params for `create_primitive` ✅
- It injects `object_name = step.target` if `object_name` not in params for `set_transform`, `duplicate_object` etc. ✅ (but this is wrong — the schema requires `name`, not `object_name` for those tools)

The partial normalization actually makes things *worse* for `set_transform` and `duplicate_object`:
- LLM provides `object_name` in parameters
- Code only injects `object_name` if missing — so LLM's `object_name` is left as-is
- MCP schema requires `name` → validation fails

---

## Schema Discrepancy Table

### `set_transform` (SetTransformSchema)
| Required | LLM Sends | Validation |
|---|---|---|
| `name` | `object_name` | FAIL |

### `duplicate_object` (DuplicateObjectSchema)  
| Required | LLM Sends | Validation |
|---|---|---|
| `name` | `object_name` | FAIL |

### `delete_object` (DeleteObjectSchema)
| Required | LLM Sends | Validation |
|---|---|---|
| `name` | `object_name` | FAIL |

### `create_primitive` (CreatePrimitiveSchema)
| Required | LLM Sends | Validation |
|---|---|---|
| `primitive_type` | `type` | FAIL |
| `name` | `name` | OK |

### `assign_material` (AssignMaterialSchema)
| Required | LLM Sends | Validation |
|---|---|---|
| `object_name` | `object_name` | OK |
| `material_name` | `material` | FAIL |

---

## Source of Truth

The canonical schema is `mcp_servers/blender/schemas.py`.

These schemas are also what the Blender bridge validates — they cannot be weakened without breaking bridge compatibility.

---

## Fix Location

The fix belongs in `generation_agent.py` → `_execute_core_operation`.

This is the correct normalization layer between the LLM's unstructured parameters and the MCP tool's validated schema. It already does partial normalization — it needs to be extended to cover all field-name mismatches.

**Preferred approach:** Normalize field names in `_execute_core_operation` — this is the minimal, targeted fix with no blast radius.

**Not preferred:** Modifying `ModelingPlan.parameters` type to enforce MCP schemas (too large a change, breaks planning agent flexibility) or modifying MCP schemas (breaks bridge).

---

## Files to Modify

- `agents/generation_agent.py` — `_execute_core_operation` method only
