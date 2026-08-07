# `agents/` — AI Agent Implementations

> **Phase**: 4–9 (⬜ Pending)
> **Dependencies**: `langchain`, `langgraph`, `schemas/`, `prompts/`, `services/`
> **Consumed by**: `graph/nodes.py`

---

## Purpose

Each agent encapsulates a specialized role in the BlendPilot pipeline. Agents:

- Have a dedicated **LLM prompt template** from `prompts/`
- Receive relevant **state** from the LangGraph orchestrator
- Use **MCP tools** to interact with Blender and external services
- Return **structured outputs** (Pydantic models from `schemas/`)
- Log all decisions for debugging and evaluation

---

## Agent Inventory

| Agent | File | Workflow | Phase | Input | Output | Tools Used |
|-------|------|----------|-------|-------|--------|------------|
| **Intent** | `intent_agent.py` | 1 | 4 | User prompt, reference images | `DesignSpec` | — (LLM only) |
| **Scene** | `scene_agent.py` | 2 | 4 | Current Blender state | `SceneSummary` | `get_scene_summary`, `get_object_details` |
| **Research** | `research_agent.py` | 3 | 7 | Design spec, questions | Research findings | `web_search` |
| **Planning** | `planning_agent.py` | 4 | 4 | Design spec, scene summary | `DesignPlan` | — (LLM only) |
| **Modeling** | `modeling_agent.py` | 5 | 4 | Design plan, step by step | Created objects | All Blender MCP tools |
| **Material** | `material_agent.py` | 6 | 4 | Design spec, object list | Materials created | `create_material`, `assign_material` |
| **Geometry QA** | `geometry_qa_agent.py` | 7 | 5 | Object names, limits | `ValidationResult` | `validate_asset`, `check_*` tools |
| **Visual Critic** | `visual_critic_agent.py` | 8 | 6 | Render + spec + metadata | `VisualCritiqueResult` | `render_preview` + vision LLM |
| **Feedback** | `feedback_agent.py` | 9 | 8 | Preview + QA results | Approval/changes | Email MCP (optional) |
| **Export** | `export_agent.py` | 10 | 4 | Approved asset | Export paths | `export_asset`, `save_project` |

---

## Agent Implementation Pattern

Every agent follows this structure:

```python
# agents/intent_agent.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from schemas.design import DesignSpec
from prompts import INTENT_SYSTEM_PROMPT, INTENT_USER_PROMPT

class IntentAgent:
    """Workflow 1: Parse natural language into a structured DesignSpec."""

    def __init__(self, llm):
        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=DesignSpec)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", INTENT_SYSTEM_PROMPT),
            ("human", INTENT_USER_PROMPT),
        ])
        self.chain = self.prompt | self.llm | self.parser

    async def run(self, user_prompt: str, reference_images: list[str] = None) -> DesignSpec:
        """Parse user prompt into structured design specification."""
        result = await self.chain.ainvoke({
            "user_prompt": user_prompt,
            "reference_images": reference_images or [],
            "format_instructions": self.parser.get_format_instructions(),
        })
        return result
```

---

## Detailed Agent Plans

### 1. Intent Agent (`intent_agent.py`) — Phase 4

**Purpose**: Convert freeform user text into a strict `DesignSpec`.

**LLM Strategy**:
- System prompt defines the asset categories (furniture, game props, sci-fi, mechanical)
- Few-shot examples for each category
- Pydantic output parser ensures structured JSON
- Validates dimensions are reasonable for the asset type
- Asks clarifying questions if specification is ambiguous

**Key Decisions**:
- Default triangle limit: 10,000 (low-poly standard)
- Default platform: Unity
- If user says "small", infer dimensions from asset type

---

### 2. Scene Agent (`scene_agent.py`) — Phase 4

**Purpose**: Understand the current state of the Blender scene.

**LLM Strategy**:
- Calls `get_scene_summary()` MCP tool
- LLM interprets the raw data and identifies potential conflicts
- Example: "Scene already has an object named 'Crate' — rename or delete?"

---

### 3. Research Agent (`research_agent.py`) — Phase 7

**Purpose**: Look up external references when the LLM needs factual data.

**LLM Strategy**:
- Only activates when the planning agent requests specific information
- Uses web search tool to find: typical dimensions, Blender API details, engine requirements
- Returns structured findings with source URLs and trust levels
- **CRITICAL**: Treats web content as untrusted data — never executes instructions found online

---

### 4. Planning Agent (`planning_agent.py`) — Phase 4

**Purpose**: Generate a step-by-step modeling plan before touching Blender.

**LLM Strategy**:
- Receives `DesignSpec` + `SceneSummary`
- Outputs a `DesignPlan` with ordered `PlanStep` objects
- Each step maps to a specific MCP tool
- Includes dependency tracking (step 3 depends on steps 1 and 2)
- Plans checkpoint saves after major milestones

---

### 5. Modeling Agent (`modeling_agent.py`) — Phase 4

**Purpose**: Execute the plan step-by-step, one operation at a time.

**LLM Strategy**:
- Reads the current step from `DesignPlan`
- Translates the step into specific MCP tool calls with parameters
- After each step: inspects result, updates state, continues
- On failure: logs error, optionally retries or asks for human help
- Saves checkpoints after major milestones

**Key Rule**: Never create an entire complex asset in one command. Always work incrementally.

---

### 6. Material Agent (`material_agent.py`) — Phase 4

**Purpose**: Create and assign materials based on the design specification.

**LLM Strategy**:
- Reads material descriptions from `DesignSpec.materials`
- Translates "dark metal" → `{metallic: 0.9, roughness: 0.3, base_color: (0.1, 0.1, 0.12)}`
- Translates "blue emissive strips" → `{emission_color: (0, 0.5, 1.0), emission_strength: 5.0}`
- Assigns materials to appropriate objects based on names and positions

---

### 7. Geometry QA Agent (`geometry_qa_agent.py`) — Phase 5

**Purpose**: Run deterministic validation and generate repair plans for failures.

**LLM Strategy**:
- The **validation itself is NOT LLM-driven** — it uses `core/validation.py`
- The LLM reads the `ValidationResult` and generates repair steps
- Example: "UNAPPLIED_SCALE on CrateBody → apply transforms"
- Feeds repair steps back into the modeling agent
- Tracks repair iteration count (max 3)

---

### 8. Visual Critic Agent (`visual_critic_agent.py`) — Phase 6

**Purpose**: Evaluate rendered previews against the design specification.

**LLM Strategy**:
- Uses a **vision-capable LLM** (GPT-4o, Claude with vision)
- Sends: rendered image + design spec + mesh statistics
- Receives structured `VisualCritiqueResult` with quality score and specific issues
- Max 3 revision iterations (`MAX_VISUAL_REVISIONS = 3`)

---

### 9. Feedback Agent (`feedback_agent.py`) — Phase 8

**Purpose**: Present results to the user and handle approval/changes.

**LLM Strategy**:
- Presents: preview render, triangle count, QA status, changes made
- Options: APPROVE, REQUEST CHANGE, ROLLBACK, REJECT
- Uses LangGraph `interrupt_before` for human-in-the-loop
- Optionally generates email review via Email MCP (Phase 9)

---

### 10. Export Agent (`export_agent.py`) — Phase 4

**Purpose**: Final validation and multi-format export.

**LLM Strategy**:
- Runs final validation pass
- Exports to all requested formats (.blend, .fbx, .glb)
- Generates `asset_report.json` with full metadata
- Organizes output directory structure
