"""
BlendPilot AI — Tests for Benchmark Dataset and Metrics
"""

import json
import os
import pytest

from evaluation.metrics import (
    compute_dimension_accuracy,
    compute_triangle_compliance,
    run_full_benchmark,
)


def test_benchmark_dataset_structure():
    bench_path = "evaluation/benchmark.json"
    assert os.path.exists(bench_path)

    with open(bench_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    assert len(cases) == 20
    categories = {c["category"] for c in cases}
    assert "furniture" in categories
    assert "game_props" in categories
    assert "sci_fi" in categories
    assert "mechanical" in categories

    for c in cases:
        assert "id" in c
        assert "prompt" in c
        assert "target_dimensions" in c
        assert len(c["target_dimensions"]) == 3
        assert "triangle_limit" in c


def test_dimension_accuracy_calculation():
    # Exact match
    assert compute_dimension_accuracy([1.0, 1.0, 1.0], [1.0, 1.0, 1.0]) == 1.0

    # Slight error
    score = compute_dimension_accuracy([1.1, 1.0, 1.0], [1.0, 1.0, 1.0])
    assert 0.9 <= score < 1.0


def test_triangle_compliance_calculation():
    # Under budget
    assert compute_triangle_compliance(4000, 5000) == 1.0

    # Over budget
    score = compute_triangle_compliance(6000, 5000)
    assert score < 1.0


@pytest.mark.asyncio
async def test_run_full_benchmark_sample():
    summary = await run_full_benchmark(limit=1)
    assert summary["benchmark_cases_evaluated"] == 1
    assert summary["task_completion_rate"] == 100.0
    assert "comparative_benchmark" in summary
