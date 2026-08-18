"""
BlendPilot — Tests for MCP Server and Tool Registry
"""

import pytest

from mcp_servers.blender.server import BlenderMCPServer
from services.blender_client import BlenderClient


@pytest.fixture
def mcp_server():
    client = BlenderClient(mock_mode=True)
    return BlenderMCPServer(client=client)


def test_mcp_server_initialization(mcp_server):
    assert mcp_server.name == "blendpilot-blender"
    assert len(mcp_server.list_tools()) >= 21


def test_mcp_server_langchain_tools_conversion(mcp_server):
    lc_tools = mcp_server.get_langchain_tools()
    assert len(lc_tools) >= 21
    tool_names = [t["function"]["name"] for t in lc_tools]
    assert "create_primitive" in tool_names
    assert "validate_asset" in tool_names
    assert "render_preview" in tool_names


@pytest.mark.asyncio
async def test_mcp_server_call_primitive(mcp_server):
    res = await mcp_server.call_tool(
        "create_primitive",
        {"primitive_type": "cube", "name": "TestCube",
            "dimensions": [1.0, 1.0, 1.0]},
    )
    assert res["success"] is True
    assert "result" in res


@pytest.mark.asyncio
async def test_mcp_server_call_invalid_tool(mcp_server):
    res = await mcp_server.call_tool("non_existent_tool", {})
    assert res["success"] is False
    assert "not registered" in res["error"]


@pytest.mark.asyncio
async def test_mcp_server_validation_tool(mcp_server):
    res = await mcp_server.call_tool(
        "validate_asset",
        {"object_name": "TestCube", "triangle_limit": 5000},
    )
    assert res["success"] is True
    assert res["status"] in ["PASS", "FAIL"]


@pytest.mark.asyncio
async def test_live_client_does_not_simulate_a_disconnected_bridge():
    client = BlenderClient(port=1, timeout=0.01)
    response = await client.execute("create_primitive", {"primitive_type": "cube", "name": "ShouldNotExist"})

    assert response.success is False
    assert response.error and "Blender Bridge unavailable" in response.error
