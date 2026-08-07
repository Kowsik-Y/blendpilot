# `evaluation/` — Benchmarks & Metrics

> **Phase**: 10 (⬜ Pending)
> **Dependencies**: `matplotlib`, `schemas/`
> **Consumed by**: Capstone report & research paper

---

## Purpose

The evaluation framework quantifies BlendPilot's performance against the capstone research question:

> Can a stateful agentic AI system autonomously transform high-level design requirements into editable Blender assets?

It provides:
- 20 benchmark prompts across 4 categories
- Automated metric collection per run
- Baseline vs. BlendPilot comparison
- Visualization (tables and graphs) for the capstone report

---

## Benchmark Dataset (`benchmark.json`)

20 prompts across 4 categories:

| Category | Count | Examples |
|----------|-------|---------|
| **Furniture** | 5 | dining table, office chair, bookshelf, nightstand, stool |
| **Game Props** | 5 | barrel, treasure chest, wooden crate, stone well, wooden door |
| **Sci-Fi** | 5 | supply crate, control panel, power cell, cargo pod, vending machine |
| **Mechanical** | 5 | gear wheel, bolt & nut, pipe connector, lever switch, piston |

---

## Metrics to Record

| Metric | Type | Description |
|--------|------|-------------|
| `task_completion` | bool | Did the system produce a valid export? |
| `design_satisfaction` | float (0–1) | How well does the result match the spec? |
| `dimension_accuracy` | float | Absolute error from target dimensions (meters) |
| `triangle_compliance` | bool | Was the triangle budget respected? |
| `tool_call_success_rate` | float (0–1) | % of MCP tool calls that succeeded |
| `geo_qa_pass` | bool | Did geometry QA pass? |
| `auto_repairs` | int | Number of automatically repaired issues |
| `visual_quality_score` | float (0–1) | Score from visual critic |
| `repair_iterations` | int | Number of QA → repair cycles |
| `export_success` | bool | Was the export produced correctly? |
| `human_interventions` | int | Number of times human had to intervene |
| `total_tool_calls` | int | Total MCP tool calls in the run |
| `total_time_seconds` | float | Wall-clock time from prompt to export |

---

## Comparison Modes

### Baseline

```
Prompt → LLM → Single Blender generation pass → Export
```

No planning, no QA, no repair, no visual critique.

### BlendPilot (Full Pipeline)

```
Prompt → Intent → Plan → Model → QA → Repair → Visual QA → Repair → Export
```

Full agentic pipeline with all 10 workflows.

---

## `metrics.py` Implementation Plan

```python
class BenchmarkRunner:
    """Runs all 20 benchmark prompts and collects metrics."""

    async def run_benchmark(self, mode: str = "blendpilot") -> BenchmarkReport:
        """Run all prompts and return aggregated results."""
        ...

    async def run_single(self, prompt: str, mode: str) -> RunMetrics:
        """Run a single prompt and collect metrics."""
        ...

    def compare(self, baseline: BenchmarkReport, blendpilot: BenchmarkReport) -> ComparisonReport:
        """Compare baseline vs. BlendPilot results."""
        ...

    def generate_report(self, comparison: ComparisonReport, output_dir: str):
        """Generate tables and graphs for the capstone paper."""
        # Table: per-prompt results
        # Graph: success rates by category
        # Graph: repair iteration distribution
        # Graph: visual quality scores
        ...
```
