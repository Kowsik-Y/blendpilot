"""
BlendPilot — Tests for The 10 Specialized Agents
"""

import pytest

from agents.export_agent import ExportAgent
from agents.feedback_agent import FeedbackAgent
from agents.geometry_qa_agent import GeometryQAAgent
from agents.intent_agent import IntentAgent
from agents.material_agent import MaterialAgent
from agents.modeling_agent import ModelingAgent
from agents.planning_agent import PlanningAgent
from agents.research_agent import ResearchAgent
from agents.scene_agent import SceneAgent
from agents.visual_critic_agent import VisualCriticAgent
from mcp_servers.blender.server import BlenderMCPServer
from schemas.design import DesignSpec, Dimensions
from schemas.plan import DesignPlan, PlanStep
from services.blender_client import BlenderClient


@pytest.fixture
def mock_mcp_server():
    client = BlenderClient(mock_mode=True)
    return BlenderMCPServer(client=client)


@pytest.mark.asyncio
async def test_intent_agent_parsing():
    agent = IntentAgent()
    spec = await agent.execute(
        user_prompt="Create a low-poly sci-fi supply crate for Unity. Dimensions: 1.0m x 0.7m x 0.6m. Triangle budget: 8000. Dark metal with blue emissive strip.",
    )
    assert isinstance(spec, DesignSpec)
    assert spec.asset_type == "crate"
    assert spec.style == "sci-fi"
    assert spec.target_platform == "Unity"
    assert spec.triangle_limit == 8000
    assert spec.dimensions.width == 1.0
    assert spec.dimensions.depth == 0.7
    assert spec.dimensions.height == 0.6


@pytest.mark.asyncio
async def test_notebook_uses_a_notebook_specific_plan():
    spec = await IntentAgent().execute(user_prompt="Create a notebook")
    plan = await PlanningAgent().execute(spec)

    assert spec.asset_type == "notebook"
    assert any(step.parameters.get("name") ==
               "Notebook_Pages" for step in plan.steps)
    assert any(step.parameters.get("name") ==
               "Notebook_Cover" for step in plan.steps)


@pytest.mark.asyncio
async def test_scene_agent(mock_mcp_server):
    agent = SceneAgent(mcp_server=mock_mcp_server)
    scene = await agent.execute()
    assert scene is not None
    assert isinstance(scene.objects, list)


@pytest.mark.asyncio
async def test_research_agent():
    agent = ResearchAgent()
    spec = DesignSpec(
        asset_type="table",
        style="low-poly",
        dimensions=Dimensions(width=1.2, depth=0.8, height=0.75),
        triangle_limit=5000,
        target_platform="Unity",
    )
    findings = await agent.execute(spec)
    assert len(findings) >= 2
    assert any(f["category"] == "platform_constraints" for f in findings)


@pytest.mark.asyncio
async def test_planning_agent():
    agent = PlanningAgent()
    spec = DesignSpec(
        asset_type="crate",
        style="sci-fi",
        dimensions=Dimensions(width=1.0, depth=0.7, height=0.6),
        triangle_limit=8000,
        target_platform="Unity",
    )
    plan = await agent.execute(spec)
    assert isinstance(plan, DesignPlan)
    assert len(plan.steps) >= 3
    assert plan.steps[0].tool == "create_primitive"


@pytest.mark.asyncio
async def test_modeling_agent(mock_mcp_server):
    plan_agent = PlanningAgent()
    spec = DesignSpec(
        asset_type="crate",
        style="sci-fi",
        dimensions=Dimensions(width=1.0, depth=0.7, height=0.6),
        triangle_limit=8000,
        target_platform="Unity",
    )
    plan = await plan_agent.execute(spec)
    model_agent = ModelingAgent(mcp_server=mock_mcp_server)
    result = await model_agent.execute(plan)

    assert result["success"] is True
    assert len(result["created_objects"]) >= 1


@pytest.mark.asyncio
async def test_modeling_agent_emits_live_tool_events(mock_mcp_server):
    events = []

    async def collect_event(payload):
        events.append(payload)

    plan = DesignPlan(
        spec_id="test_live_events",
        steps=[
            PlanStep(
                step_id=1,
                description="Create live preview cube",
                tool="create_primitive",
                parameters={"primitive_type": "cube", "name": "Live_Cube"},
            ),
            PlanStep(
                step_id=2,
                description="Add bevel to live preview cube",
                tool="add_modifier",
                parameters={"object_name": "Live_Cube",
                            "modifier_type": "BEVEL"},
                dependencies=[1],
            ),
        ],
    )
    model_agent = ModelingAgent(
        mcp_server=mock_mcp_server, event_callback=collect_event)
    result = await model_agent.execute(plan)

    assert result["success"] is True
    assert [event["event"] for event in events] == [
        "tool_start",
        "tool_result",
        "tool_start",
        "tool_result",
    ]
    assert events[0]["tool"] == "create_primitive"
    assert events[1]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_material_agent(mock_mcp_server):
    spec = DesignSpec(
        asset_type="crate",
        style="sci-fi",
        dimensions=Dimensions(width=1.0, depth=0.7, height=0.6),
        triangle_limit=8000,
        target_platform="Unity",
        materials=["dark_metal", "blue_emissive"],
    )
    mat_agent = MaterialAgent(mcp_server=mock_mcp_server)
    result = await mat_agent.execute(spec, created_objects=["Crate_Main", "Crate_Accent"])

    assert result["success"] is True
    assert len(result["materials"]) >= 1


@pytest.mark.asyncio
async def test_geometry_qa_agent(mock_mcp_server):
    spec = DesignSpec(
        asset_type="crate",
        style="sci-fi",
        dimensions=Dimensions(width=1.0, depth=0.7, height=0.6),
        triangle_limit=8000,
        target_platform="Unity",
    )
    qa_agent = GeometryQAAgent(mcp_server=mock_mcp_server)
    res = await qa_agent.execute(spec, created_objects=["Crate_Main"])

    assert res["status"] in ["PASS", "FAIL"]
    assert 0.0 <= res["score"] <= 1.0


@pytest.mark.asyncio
async def test_visual_critic_agent():
    spec = DesignSpec(
        asset_type="crate",
        style="sci-fi",
        dimensions=Dimensions(width=1.0, depth=0.7, height=0.6),
        triangle_limit=8000,
        target_platform="Unity",
    )
    critic = VisualCriticAgent()
    res = await critic.execute(spec, preview_image_path="output/preview.png", revision_count=0)

    assert res.overall_score >= 0.0
    assert len(res.strengths) > 0


@pytest.mark.asyncio
async def test_feedback_agent_approval():
    agent = FeedbackAgent()
    spec = DesignSpec(
        asset_type="crate",
        style="sci-fi",
        dimensions=Dimensions(width=1.0, depth=0.7, height=0.6),
    )
    plan = DesignPlan(
        spec_id="test",
        steps=[PlanStep(step_id=1, action="Create body",
                        tool="create_primitive")],
    )
    res = await agent.execute(spec, plan, action="APPROVE")

    assert res["status"] == "APPROVED"
    assert res["approved"] is True


@pytest.mark.asyncio
async def test_feedback_agent_revision():
    agent = FeedbackAgent()
    spec = DesignSpec(
        asset_type="crate",
        style="sci-fi",
        dimensions=Dimensions(width=1.0, depth=0.7, height=0.6),
    )
    plan = DesignPlan(
        spec_id="test",
        steps=[PlanStep(step_id=1, action="Create body",
                        tool="create_primitive")],
    )
    res = await agent.execute(spec, plan, feedback_text="Make it taller and wider", action="REQUEST_CHANGE")

    assert res["status"] == "REVISION_REQUESTED"
    assert res["approved"] is False
    assert len(res["revision_plan"].steps) >= 1


@pytest.mark.asyncio
async def test_export_agent(mock_mcp_server):
    spec = DesignSpec(
        asset_type="crate",
        style="sci-fi",
        dimensions=Dimensions(width=1.0, depth=0.7, height=0.6),
    )
    agent = ExportAgent(mcp_server=mock_mcp_server)
    res = await agent.execute(spec, created_objects=["Crate_Main"], output_dir="output")

    assert res["success"] is True
    assert len(res["exported_files"]) >= 3
    assert any(f.endswith(".json") for f in res["exported_files"])
