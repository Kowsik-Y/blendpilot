"""
BlendPilot AI — Tests for STAGE 17 Evaluation Framework
"""

import json
import os
import pytest

from scripts.benchmark import run_benchmark


@pytest.mark.asyncio
async def test_benchmark_script_mock_mode(tmp_path):
    """
    Run the benchmark script in mock mode on a single prompt to ensure
    execution, aggregation, and JSON/CSV exporting works properly.
    """
    json_path = tmp_path / "benchmark_results.json"
    csv_path = tmp_path / "benchmark_results.csv"
    
    # Run benchmark with limit=1 to test logic without heavy execution
    await run_benchmark(output_json=str(json_path), output_csv=str(csv_path), limit=1)
    
    # Verify JSON output
    assert os.path.exists(json_path)
    with open(json_path, "r") as f:
        data = json.load(f)
        
    assert "summary" in data
    assert "baseline" in data["summary"]
    assert "self_correcting" in data["summary"]
    
    assert "runs" in data
    assert len(data["runs"]) == 2  # 1 baseline, 1 self-correcting
    
    for run in data["runs"]:
        assert "prompt" in run
        assert "mode" in run
        assert "generation_success" in run
        assert "geometry_pass" in run
        assert "vision_pass" in run
        assert "execution_time_sec" in run
        assert "iterations" in run
        
    # Verify CSV output
    assert os.path.exists(csv_path)
    with open(csv_path, "r") as f:
        lines = f.readlines()
        assert len(lines) == 3  # Header + 2 runs
