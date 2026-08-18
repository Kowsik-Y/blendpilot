"""
BlendPilot — Export & Download API Endpoints

Provides zip packaging and direct downloads for exported 3D assets (.blend, .fbx, .glb, report).
"""

from __future__ import annotations

import io
import os
import zipfile
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

logger = logging = __import__("logging").getLogger("blendpilot.api.export")

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get("/{asset_name}/download")
async def download_asset_bundle(asset_name: str) -> Response:
    """Download a zip archive containing all exported files (.blend, .fbx, .glb, preview, report) for an asset."""
    asset_dir = os.path.join("output", asset_name)
    if not os.path.exists(asset_dir) or not os.path.isdir(asset_dir):
        raise HTTPException(
            status_code=404, detail=f"Asset directory '{asset_name}' not found in output")

    # Build zip in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, _, files in os.walk(asset_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, asset_dir)
                zip_file.write(file_path, arcname)

    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={asset_name}_bundle.zip"},
    )


@router.get("/{asset_name}/report")
async def get_asset_report(asset_name: str) -> dict[str, Any]:
    """Retrieve the JSON asset report for a generated 3D asset."""
    report_path = os.path.join("output", asset_name, "asset_report.json")
    if not os.path.exists(report_path):
        raise HTTPException(
            status_code=404, detail=f"Asset report for '{asset_name}' not found")

    import json
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data
