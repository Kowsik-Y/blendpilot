# `graph/` — LangGraph Orchestration

> **Phase**: 4 (⬜ Pending)
> **Dependencies**: `langgraph`, `langchain`, `schemas/`, `agents/`
> **Consumed by**: `backend/api/`

---

## Purpose

The LangGraph orchestrator is the **brain** of BlendPilot. It defines a state machine with 10 workflow nodes that processes a user's design request from natural language to exported 3D asset. Key features:

- **Typed state** (`BlendPilotState`) flowing through all nodes
- **Conditional routing** (QA pass/fail → repair or proceed)
- **Human-in-the-loop** interruption at approval points
- **Checkpoint persistence** for rollback and resumption
- **Maximum iteration guards** to prevent infinite loops

---

## Directory Structure

```
graph/
├── __init__.py
├── state.py           # BlendPilotState TypedDict (✅ implemented)
├── graph.py           # Main StateGraph definition with all nodes and edges
├── nodes.py           # Node functions that call agents
├── routes.py          # Conditional edge routing logic
└── persistence.py     # SQLite/PostgreSQL checkpoint persistence
```

---

## State Machine Diagram

```
                    START
                      │
                      ▼
              ┌──────────────┐
              │ Intent Node  │  ← Workflow 1
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ Scene Node   │  ← Workflow 2
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │Research Node │  ← Workflow 3 (optional)
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ Plan Node    │  ← Workflow 4
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ Model Node   │  ← Workflow 5 (loop over plan steps)
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │Material Node │  ← Workflow 6
              └──────┬───────┘
                     ▼
              ┌──────────────┐
          ┌──►│ Geo QA Node  │  ← Workflow 7
          │   └──────┬───────┘
          │          │
          │    ┌─────┴─────┐
          │    │            │
          │  FAIL         PASS
          │    │            │
          │    ▼            ▼
          │  ┌──────┐  ┌──────────────┐
          └──│Repair│  │Visual QA Node│  ← Workflow 8
             └──────┘  └──────┬───────┘
                              │
                        ┌─────┴─────┐
                        │           │
                      FAIL        PASS
                        │           │
                        ▼           ▼
                    ┌──────┐  ┌──────────────┐
                    │Repair│  │ Approve Node │  ← Workflow 9 (HITL interrupt)
                    └──┬───┘  └──────┬───────┘
                       │             │
                       └──► Visual   │
                            QA Node  │
                                     ▼
                              ┌──────────────┐
                              │ Export Node  │  ← Workflow 10
                              └──────┬───────┘
                                     ▼
                                    END
```

---

## Implementation Plan

### `state.py` — BlendPilotState (✅ Done)

Already implemented with all required fields:
- Project metadata (`project_id`, `user_prompt`)
- Per-workflow outputs (`design_spec`, `scene_summary`, `design_plan`, etc.)
- QA scores (`geometry_score`, `visual_score`)
- Revision control (`revision_count`, `max_revisions`)
- Approval tracking (`human_feedback`, `approval_status`)
- Error tracking (`errors`)

### `graph.py` — StateGraph Definition

```python
from langgraph.graph import StateGraph, END
from graph.state import BlendPilotState
from graph.nodes import *
from graph.routes import *

graph = StateGraph(BlendPilotState)

# Add nodes
graph.add_node("intent", intent_node)
graph.add_node("scene", scene_node)
graph.add_node("research", research_node)
graph.add_node("plan", plan_node)
graph.add_node("model", model_node)
graph.add_node("material", material_node)
graph.add_node("geo_qa", geo_qa_node)
graph.add_node("geo_repair", geo_repair_node)
graph.add_node("visual_qa", visual_qa_node)
graph.add_node("visual_repair", visual_repair_node)
graph.add_node("approve", approve_node)
graph.add_node("export", export_node)

# Add edges
graph.set_entry_point("intent")
graph.add_edge("intent", "scene")
graph.add_edge("scene", "research")
graph.add_edge("research", "plan")
graph.add_edge("plan", "model")
graph.add_edge("model", "material")
graph.add_edge("material", "geo_qa")

# Conditional routing
graph.add_conditional_edges("geo_qa", route_geo_qa, {
    "pass": "visual_qa",
    "fail": "geo_repair",
    "max_retries": "visual_qa",
})
graph.add_edge("geo_repair", "geo_qa")

graph.add_conditional_edges("visual_qa", route_visual_qa, {
    "pass": "approve",
    "fail": "visual_repair",
    "max_retries": "approve",
})
graph.add_edge("visual_repair", "visual_qa")

graph.add_conditional_edges("approve", route_approval, {
    "approved": "export",
    "change_requested": "plan",
    "rollback": "scene",
    "rejected": END,
})
graph.add_edge("export", END)

# Compile with interrupt for human-in-the-loop
app = graph.compile(
    checkpointer=persistence.get_checkpointer(),
    interrupt_before=["approve"],
)
```

### `nodes.py` — Node Implementations

Each node function:
1. Receives the current `BlendPilotState`
2. Calls the corresponding agent
3. Returns a state update dict

### `routes.py` — Conditional Routing

```python
def route_geo_qa(state: BlendPilotState) -> str:
    if state.get("geometry_score", 0) >= 1.0:
        return "pass"
    if state.get("revision_count", 0) >= state.get("max_revisions", 3):
        return "max_retries"
    return "fail"
```

### `persistence.py` — Checkpoint Storage

Use LangGraph's built-in checkpoint persistence:
- SQLite for development
- PostgreSQL for production (optional)
- Enables rollback to any graph state

---

## Configuration

```python
MAX_GEO_QA_RETRIES = 3
MAX_VISUAL_QA_RETRIES = 3
MAX_TOTAL_REVISIONS = 10
CHECKPOINT_DB = "sqlite:///blendpilot_checkpoints.db"
```
