import os
import pytest
from mcp_servers.blender.server import BlenderMCPServer

@pytest.mark.asyncio
async def test_export_pipeline(tmp_path):
    """
    Verify the export pipeline handles .blend, .glb, and .fbx correctly.
    """
    from services.blender_client import BlenderClient
    server = BlenderMCPServer(client=BlenderClient(mock_mode=True))
    
    out_dir = tmp_path / "export_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    blend_path = str(out_dir / "test.blend")
    glb_path = str(out_dir / "test.glb")
    fbx_path = str(out_dir / "test.fbx")
    
    # 1. Test .blend export
    res_blend = await server.call_tool("save_project", {"filepath": blend_path})
    if not res_blend.get("success") and "Ensure Blender is running" in str(res_blend.get("error", "")):
        pytest.skip("Blender bridge is not running. Skipping integration test.")
        
    assert os.path.exists(blend_path), f"File was not written to {blend_path}"
    assert os.path.getsize(blend_path) > 0, "Rendered .blend file is empty"
    
    # We must have at least one object to export. Let's create a primitive.
    await server.call_tool("create_primitive", {"primitive_type": "cube", "name": "TestCube"})
    
    # 2. Test .glb export
    res_glb = await server.call_tool("export_asset", {
        "object_names": ["TestCube"],
        "output_path": glb_path,
        "format": "GLB"
    })
    
    assert res_glb.get("success") is True, f"GLB Export failed: {res_glb}"
    assert os.path.exists(glb_path), f"File was not written to {glb_path}"
    assert os.path.getsize(glb_path) > 0, "Rendered .glb file is empty"
    
    # 3. Test .fbx export
    res_fbx = await server.call_tool("export_asset", {
        "object_names": ["TestCube"],
        "output_path": fbx_path,
        "format": "FBX"
    })
    
    assert res_fbx.get("success") is True, f"FBX Export failed: {res_fbx}"
    assert os.path.exists(fbx_path), f"File was not written to {fbx_path}"
    assert os.path.getsize(fbx_path) > 0, "Rendered .fbx file is empty"
