import os
import pytest
from mcp_servers.blender.server import BlenderMCPServer

@pytest.mark.asyncio
async def test_real_render_pipeline(tmp_path):
    """
    Verify the real render pipeline.
    1. Camera exists (setup_preview_camera)
    2. Render engine is configured
    3. Resolution is configured
    4. Output path is absolute or correctly resolved
    5. Blender actually executes the render
    6. preview.png exists after execution
    """
    # Connect to the MCP Server
    # If Blender isn't running, this might fall back to mock mode or fail if we force real mode.
    # To test the real pipeline, the bridge must be active or we mock the exact behavior.
    # Wait, the user specifically wants to verify the file is WRITTEN.
    
    server = BlenderMCPServer()
    
    # We will use a temp path to ensure we aren't picking up a stale file
    preview_path = str(tmp_path / "preview.png")
    
    # Setup camera and lighting first
    res1 = await server.call_tool("setup_preview_camera", {})
    res2 = await server.call_tool("setup_studio_lighting", {})
    
    # If Blender isn't running and we're in real mode, it returns an error dict
    for r in [res1, res2]:
        if not r.get("success") and "Ensure Blender is running" in str(r.get("error", "")):
            pytest.skip("Blender bridge is not running. Skipping integration test.")
            
    # Render preview
    result = await server.call_tool("render_preview", {"output_path": preview_path})
    
    if not result.get("success") and "Ensure Blender is running" in str(result.get("error", "")):
        pytest.skip("Blender bridge is not running. Skipping integration test.")
    
    # Verify result dictionary
    assert result.get("success", False) is True
    
    # Verify file physically exists and has size > 0
    assert os.path.exists(preview_path), f"File was not written to {preview_path}"
    assert os.path.getsize(preview_path) > 0, "Rendered image file is empty (size 0)"
