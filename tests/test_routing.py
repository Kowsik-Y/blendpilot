"""
BlendPilot AI - Stage 12 Routing tests.
"""

from graph.graph import route_after_decision
from graph.state import BlendPilotState

def test_decision_pass_both():
    """Test that a passed validation and vision report routes to export_node."""
    state = BlendPilotState(
        user_prompt="Make a table",
        iteration_count=1,
        validation_report={"passed": True, "checks": []},
        vision_report={"overall_result": "PASS", "obvious_visual_errors": []}
    )
    assert route_after_decision(state) == "export_node"

def test_decision_fail_geometry_repairable():
    """Test that repairable geometry errors route to repair_node."""
    state = BlendPilotState(
        user_prompt="Make a table",
        iteration_count=1,
        validation_report={
            "passed": False,
            "checks": [{"severity": "medium", "check_name": "duplicate_vertices"}]
        },
        vision_report={"overall_result": "PASS"}
    )
    assert route_after_decision(state) == "repair_node"

def test_decision_fail_vision_repairable():
    """Test that repairable vision errors route to repair_node."""
    state = BlendPilotState(
        user_prompt="Make a table",
        iteration_count=1,
        validation_report={"passed": True, "checks": []},
        vision_report={"overall_result": "FAIL"}
    )
    assert route_after_decision(state) == "repair_node"

def test_decision_fail_geometry_critical():
    """Test that critical geometry errors route to planner_node."""
    state = BlendPilotState(
        user_prompt="Make a table",
        iteration_count=1,
        validation_report={
            "passed": False,
            "checks": [{"severity": "critical", "check_name": "missing_required_object"}]
        },
        vision_report={"overall_result": "PASS"}
    )
    assert route_after_decision(state) == "planner_node"

def test_decision_max_iterations():
    """Test that max iterations (>= 3) route to human_review_node regardless of errors."""
    state = BlendPilotState(
        user_prompt="Make a table",
        iteration_count=3,
        validation_report={
            "passed": False,
            "checks": [{"severity": "critical"}]
        },
        vision_report={"overall_result": "FAIL"}
    )
    assert route_after_decision(state) == "human_review_node"
