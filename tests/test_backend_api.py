"""
BlendPilot AI — Tests for FastAPI Backend API Endpoints
"""

import httpx
import pytest

from backend.main import app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "BlendPilot" in data["app"]


@pytest.mark.asyncio
async def test_start_workflow_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "user_prompt": "Create a wooden dining table for Unity",
            "reference_images": [],
        }
        response = await client.post("/api/workflow/start", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "session_id" in data
        assert "project_id" in data


@pytest.mark.asyncio
async def test_get_session_status():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Start a workflow
        start_res = await client.post(
            "/api/workflow/start",
            json={"user_prompt": "Create a low-poly chair"},
        )
        session_id = start_res.json()["session_id"]

        # Check status
        status_res = await client.get(f"/api/workflow/{session_id}/status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["session_id"] == session_id
