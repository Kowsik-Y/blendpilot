"""
BlendPilot AI — Tests for MCP Pydantic Schema Validation
"""

import pytest
from unittest.mock import AsyncMock

from mcp_servers.blender.server import BlenderMCPServer


@pytest.fixture
def mcp_server():
    """Provides a fresh BlenderMCPServer instance for testing."""
    # We mock the client so we don't actually hit the HTTP endpoint
    server = BlenderMCPServer(client=AsyncMock())
    
    # Mock the internal handler of create_primitive to avoid actually running Blender logic
    # We just need to verify that call_tool successfully reaches the handler or fails before it.
    for name in server._handlers:
        server._handlers[name] = AsyncMock(return_value={"success": True})
        
    return server


@pytest.mark.asyncio
async def test_mcp_validation_success(mcp_server):
    """Verify that a valid tool payload successfully passes validation."""
    result = await mcp_server.call_tool(
        name="create_primitive",
        arguments={
            "primitive_type": "cube",
            "name": "MyCube",
            "dimensions": [2.0, 2.0, 2.0],
        }
    )
    assert result.get("success") is True


@pytest.mark.asyncio
async def test_mcp_validation_missing_required_field(mcp_server):
    """Verify that missing a required field (e.g., 'name') triggers a validation error."""
    result = await mcp_server.call_tool(
        name="create_primitive",
        arguments={
            "primitive_type": "cube",
            # 'name' is omitted
        }
    )
    assert result.get("success") is False
    assert "Validation Error" in result.get("error", "")
    assert "name" in result.get("error", "")
    assert "Field required" in result.get("error", "")


@pytest.mark.asyncio
async def test_mcp_validation_invalid_type(mcp_server):
    """Verify that providing an incorrect type triggers a validation error."""
    result = await mcp_server.call_tool(
        name="set_transform",
        arguments={
            "name": "MyCube",
            "location": "not_a_list",  # Should be list[float]
        }
    )
    assert result.get("success") is False
    assert "Validation Error" in result.get("error", "")
    assert "location" in result.get("error", "")


@pytest.mark.asyncio
async def test_mcp_validation_invalid_enum(mcp_server):
    """Verify that an invalid enum value triggers a validation error."""
    result = await mcp_server.call_tool(
        name="create_primitive",
        arguments={
            "primitive_type": "pyramid",  # Not in the allowed list
            "name": "MyPyramid",
        }
    )
    assert result.get("success") is False
    assert "Validation Error" in result.get("error", "")
    assert "primitive_type" in result.get("error", "")


@pytest.mark.asyncio
async def test_mcp_validation_bounds(mcp_server):
    """Verify that numeric bounds (e.g., roughness between 0 and 1) are enforced."""
    result = await mcp_server.call_tool(
        name="create_material",
        arguments={
            "name": "ShinyMat",
            "roughness": 1.5,  # Too high, max is 1.0
        }
    )
    assert result.get("success") is False
    assert "Validation Error" in result.get("error", "")
    assert "roughness" in result.get("error", "")
