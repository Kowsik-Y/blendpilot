# BlendPilot AI — Architecture Guide

> A Self-Correcting Agentic AI Copilot for Blender

This document provides a comprehensive overview of every module in the BlendPilot project, its purpose, how it connects to other modules, and the implementation plan for each development phase.

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Streamlit UI │  │  REST API    │  │  Email Review Client │  │
│  │   (ui/)      │  │  (backend/)  │  │  (services/email)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         └─────────────────┼─────────────────────┘              │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              LangGraph Orchestrator (graph/)              │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │              BlendPilotState (graph/state.py)       │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                          │  │
│  │  Nodes: intent → scene → research → plan → model →      │  │
│  │         material → geo_qa → visual_qa → feedback →       │  │
│  │         export                                           │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               Agent Layer (agents/)                       │  │
│  │  10 specialized agents, each with its own LLM prompt     │  │
│  │  template from prompts/ and Pydantic schemas from        │  │
│  │  schemas/                                                 │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              MCP Tool Layer (mcp_servers/)                │  │
│  │  ┌─────────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │  │
│  │  │ Blender MCP │ │ File MCP │ │ Email MCP│ │Web Search│ │  │
│  │  └──────┬──────┘ └──────────┘ └──────────┘ └─────────┘ │  │
│  └─────────┼────────────────────────────────────────────────┘  │
│            ▼                                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Blender Bridge (blender_addon/bridge.py)          │  │
│  │         localhost HTTP/socket ↔ Blender Add-on            │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Core Blender Functions (core/)                    │  │
│  │  objects │ modifiers │ materials │ scene │ rendering │    │  │
│  │  validation │ project │ demo                              │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Blender Python API (bpy / bmesh)                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Reference

| Module | Phase | Purpose | Key Dependencies |
|--------|-------|---------|-----------------|
| `core/` | 1 ✅ | Direct Blender Python API wrappers | `bpy`, `bmesh` |
| `schemas/` | 1 ✅ | Pydantic data models for all workflows | `pydantic` |
| `docs/` | 1 ✅ | Per-module documentation & plans | — |
| `blender_addon/` | 2 | Blender add-on with bridge server | `bpy` |
| `mcp_servers/` | 3 | MCP tool servers for Blender operations | `mcp-sdk` |
| `graph/` | 4 | LangGraph state machine & orchestration | `langgraph` |
| `agents/` | 4–9 | 10 specialized AI agents | `langchain` |
| `prompts/` | 4 | LLM prompt templates per agent | — |
| `backend/` | 4 | FastAPI REST API | `fastapi` |
| `services/` | 3–9 | External service integrations | various |
| `ui/` | 10 | Streamlit web interface | `streamlit` |
| `evaluation/` | 10 | Benchmarks, metrics, and comparison | `matplotlib` |
| `tests/` | 1 ✅ | Test suite with bpy mocking | `pytest` |

---

## Data Flow Through the System

```
User Prompt
    │
    ▼
┌─ DesignSpec (schemas/design.py) ──────────────────────┐
│  Structured from natural language by Intent Agent       │
│  Contains: asset_type, dimensions, materials, limits    │
└────────────────────────┬──────────────────────────────┘
                         ▼
┌─ SceneSummary (schemas/scene.py) ─────────────────────┐
│  Current Blender state captured by Scene Agent          │
│  Contains: objects, cameras, lights, mesh stats         │
└────────────────────────┬──────────────────────────────┘
                         ▼
┌─ DesignPlan (schemas/plan.py) ────────────────────────┐
│  Step-by-step modeling plan from Planning Agent         │
│  Contains: ordered steps, tools, dependencies           │
└────────────────────────┬──────────────────────────────┘
                         ▼
┌─ Modeling Execution ──────────────────────────────────┐
│  Modeling Agent executes plan step-by-step via MCP      │
│  Checkpoints saved after major milestones               │
└────────────────────────┬──────────────────────────────┘
                         ▼
┌─ ValidationResult (schemas/validation.py) ────────────┐
│  Deterministic geometry QA — no LLM involved            │
│  PASS → Visual QA    FAIL → Repair → Revalidate        │
└────────────────────────┬──────────────────────────────┘
                         ▼
┌─ VisualCritiqueResult (schemas/validation.py) ────────┐
│  Vision model evaluates rendered preview                │
│  Max 3 revision iterations                              │
└────────────────────────┬──────────────────────────────┘
                         ▼
┌─ Human Approval ──────────────────────────────────────┐
│  APPROVE / REQUEST CHANGE / ROLLBACK / REJECT           │
│  LangGraph interrupt-based human-in-the-loop            │
└────────────────────────┬──────────────────────────────┘
                         ▼
┌─ Export Bundle ────────────────────────────────────────┐
│  .blend + .fbx + .glb + preview.png + asset_report.json │
└───────────────────────────────────────────────────────┘
```

---

## Phase-by-Phase Implementation Roadmap

| Phase | Name | Description | Status |
|-------|------|-------------|--------|
| 1 | Blender POC | Core Python functions, schemas, tests | ✅ Done |
| 2 | Blender Bridge | Add-on + HTTP bridge for external control | ⬜ Next |
| 3 | MCP Integration | Wrap core functions as MCP tools | ⬜ |
| 4 | LangGraph MVP | Intent → Plan → Model → Save pipeline | ⬜ |
| 5 | Geometry QA | Deterministic validation + repair loop | ⬜ |
| 6 | Vision QA | Render → Visual critique → repair loop | ⬜ |
| 7 | Web Research | External reference lookup agent | ⬜ |
| 8 | Human Approval | LangGraph interrupt-based HITL | ⬜ |
| 9 | Email MCP | Review email workflow | ⬜ |
| 10 | UI & Eval | Streamlit + 20-prompt benchmark | ⬜ |

See individual module documentation in `docs/` for detailed per-module plans.
