# BlendPilot AI

**A Self-Correcting Agentic AI Copilot for Blender**

BlendPilot AI is an autonomous agent that transforms natural-language 3D design requests into production-ready Blender assets. It uses planning, tool execution, geometric validation, visual self-critique, automatic repair, and human-in-the-loop feedback.

> **Current Status: Phase 1 — Blender Proof of Concept**

---

## Project Structure

```
blendpilot/
├── core/               ★ Phase 1 — Blender Python functions
│   ├── objects.py          Create/transform/duplicate/delete primitives
│   ├── modifiers.py        Add/apply modifiers (bevel, solidify, etc.)
│   ├── materials.py        Principled BSDF material creation & assignment
│   ├── scene.py            Scene inspection & mesh statistics
│   ├── rendering.py        Camera, studio lighting, preview renders
│   ├── validation.py       Deterministic geometry QA checks
│   ├── project.py          Checkpoints, save, FBX/GLB export
│   └── demo.py             End-to-end demo: low-poly red table
│
├── schemas/            Pydantic data models
├── blender_addon/      Blender add-on (Phase 2+)
├── mcp_servers/        MCP tool servers (Phase 3+)
├── backend/            FastAPI backend (Phase 4+)
├── graph/              LangGraph orchestrator (Phase 4+)
├── agents/             AI agent implementations (Phase 4+)
├── services/           External service clients
├── prompts/            LLM prompt templates
├── ui/                 Streamlit interface (Phase 10)
├── evaluation/         Benchmark prompts & metrics
├── tests/              Test suite with bpy mocking
└── output/             Generated assets
```

---

## Installation

### Prerequisites

- **Python 3.11+**
- **Blender 4.0+** (for running core modules inside Blender)

### Setup

```bash
# Clone the repository
cd blendpilot

# Create a virtual environment (for tests & development)
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
```

---

## Running Tests

Tests use a mock `bpy` module so they run **outside Blender**:

```bash
cd blendpilot
python -m pytest tests/ -v
```

---

## Running the Demo (Inside Blender)

### Option 1: Blender Python Console

1. Open Blender
2. Switch to the **Scripting** workspace
3. Open `core/demo.py`
4. Run the script

### Option 2: Command Line

```bash
blender --background --python -c "
import sys
sys.path.insert(0, '/path/to/blendpilot')
from core.demo import create_red_table
create_red_table(output_dir='./output/red_table')
"
```

### Option 3: Blender Script Mode

```bash
blender --background --python core/demo.py -- ./output/red_table
```

### Expected Output

```
output/red_table/
├── red_table.blend      # Editable Blender file
├── red_table.fbx        # FBX export for game engines
└── preview.png          # Rendered preview image
```

The demo creates:
- 1 tabletop (scaled cube)
- 4 legs (scaled cubes, positioned at corners)
- Red Principled BSDF material on all parts
- Bevel modifiers on all parts
- Three-point studio lighting
- Preview camera
- Rendered preview at 1920×1080

---

## Development Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Blender Proof of Concept | ✅ Current |
| 2 | External Blender Bridge | ⬜ |
| 3 | MCP Tool Integration | ⬜ |
| 4 | Minimum LangGraph Pipeline | ⬜ |
| 5 | Geometry QA Loop | ⬜ |
| 6 | Vision QA Loop | ⬜ |
| 7 | Web Research Agent | ⬜ |
| 8 | Human Approval (HITL) | ⬜ |
| 9 | Email MCP Integration | ⬜ |
| 10 | UI & Evaluation | ⬜ |

---

## Technology Stack

- **Python 3.11+** — Core language
- **Blender Python API** (`bpy`, `bmesh`) — 3D operations
- **Pydantic** — Data validation & schemas
- **LangChain / LangGraph** — Agent orchestration (Phase 4+)
- **MCP** — Model Context Protocol for tool integration (Phase 3+)
- **FastAPI** — Backend API (Phase 4+)
- **Streamlit** — User interface (Phase 10)
- **Pytest** — Testing framework

---

## License

MIT
