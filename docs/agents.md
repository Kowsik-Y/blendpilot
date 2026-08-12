# The 10 Specialized Agents

BlendPilot employs 10 hyper-specialized agents. Each agent has a distinct system prompt, toolset, and designated output Pydantic schema to ensure predictable results.

| # | Agent | Role & Responsibility | Output Schema |
|---|---|---|---|
| **1** | `IntentAgent` | Parses prompt into dimensions, target engine, and polygon limits | `DesignSpec` |
| **2** | `SceneAgent` | Scans active Blender scene for existing geometry & lights | `SceneSummary` |
| **3** | `ResearchAgent` | Retrieves platform topology guidelines (Unity/Unreal/Web) | `ResearchFindings` |
| **4** | `PlanningAgent` | Generates ordered, atomic modeling step breakdown | `DesignPlan` |
| **5** | `ModelingAgent` | Translates plan steps into MCP tool calls (primitives, modifiers, booleans) | `ModelingResult` |
| **6** | `MaterialAgent` | Creates Principled BSDF PBR shaders & 3-point studio lighting | `MaterialResult` |
| **7** | `GeometryQAAgent` | Deterministic mesh QA (non-manifold, normals, transforms, polycount) | `ValidationResult` |
| **8** | `VisualCriticAgent` | Multi-modal vision critique evaluating renders with automated repair loop | `VisualCritiqueResult` |
| **9** | `FeedbackAgent` | Human-in-the-loop review gate (`APPROVE` or `REQUEST_CHANGE`) | `FeedbackResult` |
| **10** | `ExportAgent` | Packages production `.blend`, `.fbx`, `.glb`, and metadata JSON | `ExportResult` |

---

## Agent Flow Details

### Planning & Research (Agents 1-4)
These agents never touch Blender. They construct the blueprint. By researching constraints first, the engine avoids making costly geometric errors later.

### Modeling & Materials (Agents 5-6)
These agents interact directly with the **MCP Server**. They generate tool call sequences that map to native `bpy` operators.

### Validation & Critique (Agents 7-8)
The self-repair loop is driven here.
- **Agent 7** uses deterministic math (checking vertex counts, overlapping faces).
- **Agent 8** uses a Vision-Language Model to visually inspect the render against the original prompt, scoring it on a 0-1 scale.

### Output (Agents 9-10)
Optionally pauses for a human to review the final render in the UI, before exporting the final asset bundle.
