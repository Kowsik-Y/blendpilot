# `prompts/` — LLM Prompt Templates

> **Phase**: 4 (⬜ Pending)
> **Dependencies**: —
> **Consumed by**: `agents/`

---

## Purpose

Every AI agent has a dedicated prompt template. Prompts are:

- Stored as **plain Python strings** (not external files) for easy version control
- Split into **system** (role & constraints) and **user** (per-invocation context) parts
- Include **few-shot examples** where helpful
- Include **output format instructions** for Pydantic parsing

---

## Prompt File Inventory

| File | Agent | System Prompt | User Prompt |
|------|-------|---------------|-------------|
| `intent.py` | Intent Agent | Role + asset categories + output format | User prompt + reference images |
| `scene.py` | Scene Agent | Role + interpretation rules | Raw scene data |
| `research.py` | Research Agent | Role + safety rules | Query + context |
| `planning.py` | Planning Agent | Role + planning rules + tools list | Design spec + scene summary |
| `modeling.py` | Modeling Agent | Role + tool usage rules + safety | Current step + scene state |
| `material.py` | Material Agent | Role + PBR knowledge + color mapping | Material descriptions |
| `geometry_qa.py` | Geometry QA Agent | Role + repair strategies | Validation results |
| `visual_critic.py` | Visual Critic Agent | Role + visual quality criteria | Render + spec + mesh data |
| `feedback.py` | Feedback Agent | Role + review packaging | QA results + preview |
| `export.py` | Export Agent | Role + export checklist | Asset metadata |

---

## Prompt Design Principles

1. **Explicit constraints**: Every prompt states what the agent must NOT do
2. **Structured output**: Every prompt includes format instructions for Pydantic parsing
3. **Few-shot examples**: Complex agents include 1–2 examples of expected output
4. **Safety guards**: Research and modeling prompts include security rules
5. **Scope limitation**: Each agent prompt limits the agent to its workflow only

See the individual prompt files in `prompts/` for the complete templates.
