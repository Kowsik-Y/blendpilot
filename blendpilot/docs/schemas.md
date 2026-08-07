# `schemas/` — Pydantic Data Models

> **Phase**: 1 (✅ Complete)
> **Dependencies**: `pydantic >= 2.0`
> **Consumed by**: All agents, graph state, services, API endpoints

---

## Purpose

Typed data contracts used across the entire BlendPilot system. Every workflow input/output is a Pydantic model, ensuring:

- Validation at boundaries (API input, LLM output parsing, MCP tool args)
- Serialization to/from JSON for storage, logging, and API responses
- Self-documenting interfaces between modules
- IDE auto-completion and type checking

---

## Module Inventory

### `design.py` — Design Specification (Workflow 1)

| Model | Description |
|-------|-------------|
| `Dimensions` | Width/depth/height in meters. All values must be > 0. |
| `DesignSpec` | Full structured specification parsed from user prompt. Contains asset_type, style, dimensions, triangle_limit, target_platform, materials list, export_format, description, reference_images. |

**Used by**: Intent Agent (output), Planning Agent (input), Visual Critic (reference), Export Agent (validation)

### `scene.py` — Scene Data (Workflow 2)

| Model | Description |
|-------|-------------|
| `ObjectType` | Enum: MESH, CAMERA, LIGHT, EMPTY, CURVE, OTHER |
| `TransformInfo` | Location/rotation/scale tuple |
| `ModifierInfo` | Modifier name, type, viewport visibility |
| `MaterialSlot` | Slot index + material name |
| `ObjectInfo` | Complete object info: type, transform, dimensions, parent, collection, modifiers, materials |
| `MeshStatistics` | Vertex/edge/face/triangle counts, dimensions, bounding box volume, ngon detection |
| `SceneSummary` | Full scene overview: object list, collections, camera/light presence, active object, render engine |

**Used by**: Scene Agent (output), Modeling Agent (context), Geometry QA (input)

### `plan.py` — Design Plan (Workflow 4)

| Model | Description |
|-------|-------------|
| `StepStatus` | Enum: PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED |
| `PlanStep` | Single plan step with step_id, action, target_object, expected_result, required_tool, dependencies, status |
| `DesignPlan` | Complete plan with steps list, completion tracking, `is_complete` and `current_step` properties |

**Used by**: Planning Agent (output), Modeling Agent (execution), Graph state (tracking)

### `validation.py` — Validation & Critique (Workflows 7 & 8)

| Model | Description |
|-------|-------------|
| `Severity` | Enum: LOW, MEDIUM, HIGH, CRITICAL |
| `IssueType` | Enum: 12 issue types (TRIANGLE_OVER_BUDGET, NON_MANIFOLD, FLIPPED_NORMALS, etc.) |
| `ValidationIssue` | Single issue with type, object, severity, message, auto_fixable flag |
| `ValidationResult` | Full QA result: PASS/FAIL status, triangle/vertex/face counts, issues list, severity counts, `has_critical_issues` and `auto_fixable_count` properties |
| `VisualCritiqueIssue` | Visual issue with target, problem, severity, recommended_change |
| `VisualCritiqueResult` | Vision model output: quality_score (0–1), issues, iteration tracking, recommendation |

**Used by**: Geometry QA Agent, Visual Critic Agent, Feedback Agent, Export Agent

---

## JSON Roundtrip Example

```python
from schemas.design import DesignSpec, Dimensions

spec = DesignSpec(
    asset_type="sci-fi crate",
    dimensions=Dimensions(width=1.0, depth=0.7, height=0.6),
    triangle_limit=8000,
    materials=["dark metal", "blue emissive strips"],
)

# Serialize
json_str = spec.model_dump_json(indent=2)

# Deserialize
restored = DesignSpec.model_validate_json(json_str)
assert restored == spec
```

---

## Future Schema Additions (Phase 4+)

| Schema | Phase | Purpose |
|--------|-------|---------|
| `ResearchResult` | 7 | Web search findings with URLs and source trust levels |
| `EmailReview` | 9 | Structured email review request/response |
| `BenchmarkResult` | 10 | Per-prompt evaluation metrics |
