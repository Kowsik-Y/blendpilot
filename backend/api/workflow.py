"""
BlendPilot AI — Workflow API Endpoints

Provides endpoints for launching autonomous modeling workflows and streaming
live Agent chain-of-thought and tool execution over WebSocket.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from core.agent import BlendPilotAgent

logger = logging.getLogger("blendpilot.api.workflow")

router = APIRouter(prefix="/api/workflow", tags=["Workflow"])

# In-memory session registry and event queues for active streams
_active_sessions: dict[str, dict[str, Any]] = {}
_session_event_queues: dict[str, list[asyncio.Queue]] = {}

class StartWorkflowRequest(BaseModel):
    """Payload to initiate a 3D modeling workflow."""
    user_prompt: str = Field(..., min_length=3, description="Natural-language description of the 3D asset")
    project_id: str | None = Field(default=None, description="Studio project that owns this workflow session")
    overrides: dict[str, Any] | None = Field(default=None, description="Optional manual parameter overrides including API keys")

@router.post("/start")
async def start_workflow(request: StartWorkflowRequest) -> dict[str, Any]:
    """Initiate a new dynamic LangChain agent workflow."""
    project_id = request.project_id or f"proj_{uuid.uuid4().hex[:8]}"
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    
    from services.llm import LLMService
    llm_kwargs = {}
    if request.overrides:
        if request.overrides.get("provider"): llm_kwargs["provider"] = request.overrides["provider"]
        if request.overrides.get("model"): llm_kwargs["model"] = request.overrides["model"]
        if request.overrides.get("api_key"): llm_kwargs["api_key"] = request.overrides["api_key"]
        if request.overrides.get("base_url"): llm_kwargs["base_url"] = request.overrides["base_url"]
        if request.overrides.get("temperature") is not None: llm_kwargs["temperature"] = request.overrides["temperature"]
        if request.overrides.get("max_tokens") is not None: llm_kwargs["max_tokens"] = request.overrides["max_tokens"]
        
    tavily_api_key = request.overrides.get("tavily_api_key") if request.overrides else None
    
    llm_service = LLMService(**llm_kwargs)

    # Instantiate a new stateful agent for this session
    agent = BlendPilotAgent(llm_service=llm_service, tavily_api_key=tavily_api_key)

    _active_sessions[session_id] = {
        "agent": agent,
        "status": "RUNNING",
        "project_id": project_id,
        "stream_events": [],
        "stream_event_seq": 0,
    }
    _session_event_queues[session_id] = []

    # Run execution in background task
    asyncio.create_task(_run_agent_task(session_id, request.user_prompt))

    return {
        "success": True,
        "project_id": project_id,
        "session_id": session_id,
        "status": "RUNNING",
        "message": "Modeling workflow started successfully",
    }


def _make_json_safe(obj: Any) -> Any:
    """Recursively convert an object to a JSON-serializable structure."""
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_safe(item) for item in obj]
    elif hasattr(obj, "model_dump"):
        return _make_json_safe(obj.model_dump())
    elif hasattr(obj, "dict"):
        return _make_json_safe(obj.dict())
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        return str(obj)


def _record_stream_event(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Assign a durable event id and append the payload to the session replay log."""
    if session_id not in _active_sessions:
        return payload

    session = _active_sessions[session_id]
    next_event_id = int(session.get("stream_event_seq", 0)) + 1
    safe_payload = _make_json_safe(payload)
    event_payload = {
        "event_id": next_event_id,
        **safe_payload,
    }
    session["stream_event_seq"] = next_event_id
    session.setdefault("stream_events", []).append(event_payload)
    return event_payload


async def _broadcast_event(session_id: str, payload: dict[str, Any]) -> None:
    """Send event to all active stream queues and keep replay history."""
    payload = _record_stream_event(session_id, payload)
    queues = _session_event_queues.get(session_id, [])
    for q in queues:
        await q.put(payload)


async def _run_agent_task(session_id: str, user_prompt: str) -> None:
    """Execute the LangChain agent and dispatch astream_events to listeners."""
    session = _active_sessions.get(session_id)
    if not session:
        return

    agent: BlendPilotAgent = session["agent"]
    try:
        async for event in agent.astream_events(user_prompt, session_id=session_id):
            # Format LangChain events into UI consumable payloads
            event_type = event.get("event")
            name = event.get("name")
            data = event.get("data", {})
            

            
            payload = {
                "session_id": session_id,
                "event": event_type,
                "node": name,
                "state": data,
            }
            
            if event_type == "on_tool_end":
                try:
                    summary = await agent.mcp_server.call_tool("get_scene_summary", {"include_mesh_stats": False})
                    if summary and "scene" in summary and "objects" in summary["scene"]:
                        payload["scene_objects"] = summary["scene"]["objects"]
                except Exception as e:
                    logger.warning("Failed to sync scene on tool end: %s", e)
                    
            await _broadcast_event(session_id, payload)

        session["status"] = "COMPLETED"
        scene_objects = []
        try:
            # Auto-save the Blender session so it persists across server restarts
            project_id = session.get("project_id")
            if project_id:
                import os
                os.makedirs("data/projects", exist_ok=True)
                save_path = os.path.abspath(f"data/projects/{project_id}.blend")
                await agent.mcp_server.call_tool("save_project", {"filepath": save_path})

            summary = await agent.mcp_server.call_tool("get_scene_summary", {"include_mesh_stats": False})
            if summary and "scene" in summary and "objects" in summary["scene"]:
                scene_objects = summary["scene"]["objects"]
        except Exception as e:
            logger.error("Failed to fetch final scene state: %s", e)

        await _broadcast_event(session_id, {
            "session_id": session_id,
            "event": "workflow_complete",
            "status": "COMPLETED",
            "scene_objects": scene_objects
        })

    except Exception as e:
        logger.exception("Agent error in session %s: %s", session_id, e)
        session["status"] = "FAILED"
        await _broadcast_event(session_id, {
            "session_id": session_id, 
            "event": "workflow_failed", 
            "error": str(e), 
            "status": "FAILED"
        })


def _is_terminal_stream_event(data: dict[str, Any]) -> bool:
    """Only full workflow terminal events should close live transports."""
    if data.get("event") == "workflow_complete":
        return True
    return data.get("status") == "FAILED"


@router.websocket("/{session_id}/ws")
async def websocket_workflow_progress(websocket: WebSocket, session_id: str) -> None:
    """Stream agent chain-of-thought and progress over WebSocket."""
    if session_id not in _active_sessions:
        await websocket.accept()
        await websocket.send_json({
            "event": "workflow_missing",
            "session_id": session_id,
            "status": "FAILED",
            "error": "Session not found",
        })
        await websocket.close(code=4404, reason="Session not found")
        return

    await websocket.accept()
    after_event_id = 0
    try:
        after_event_id = int(websocket.query_params.get("after", "0"))
    except ValueError:
        after_event_id = 0

    queue: asyncio.Queue = asyncio.Queue()
    if session_id not in _session_event_queues:
        _session_event_queues[session_id] = []
    _session_event_queues[session_id].append(queue)

    try:
        session = _active_sessions[session_id]
        # Send initial connection success
        await websocket.send_json({
            "event": "connected",
            "event_id": int(session.get("stream_event_seq", 0)),
        })

        for stream_event in session.get("stream_events", []):
            if int(stream_event.get("event_id", 0)) > after_event_id:
                await websocket.send_json(_make_json_safe(stream_event))

        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=20)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({
                        "event": "ping",
                        "session_id": session_id,
                        "event_id": int(_active_sessions[session_id].get("stream_event_seq", 0)),
                    })
                except Exception:
                    break
                continue

            try:
                await websocket.send_json(_make_json_safe(data))
            except Exception:
                break
                
            if _is_terminal_stream_event(data):
                break
    except WebSocketDisconnect:
        pass
    finally:
        if session_id in _session_event_queues and queue in _session_event_queues[session_id]:
            _session_event_queues[session_id].remove(queue)


@router.get("/scene")
async def get_scene(project_id: str | None = None) -> dict[str, Any]:
    """Fetch the ground-truth scene summary, loading the project .blend if it exists."""
    from mcp_servers.blender.server import BlenderMCPServer
    import os
    try:
        # Create a transient connection to fetch the summary
        server = BlenderMCPServer()
        
        # Auto-load the saved project session if available
        if project_id:
            save_path = os.path.abspath(f"data/projects/{project_id}.blend")
            if os.path.exists(save_path):
                await server.call_tool("restore_checkpoint", {"filepath": save_path})
            else:
                # It's a new project, clear the current Blender scene
                current_summary = await server.call_tool("get_scene_summary", {"include_mesh_stats": False})
                if current_summary and "scene" in current_summary and "objects" in current_summary["scene"]:
                    for obj in current_summary["scene"]["objects"]:
                        await server.call_tool("delete_object", {"name": obj["name"]})
                
        summary = await server.call_tool("get_scene_summary", {"include_mesh_stats": False})
        return summary
    except Exception as e:
        logger.error("Error fetching scene: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/status")
async def get_session_status(session_id: str) -> dict[str, Any]:
    """Get the current execution status of a session."""
    if session_id not in _active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _active_sessions[session_id]

    return {
        "session_id": session_id,
        "project_id": session.get("project_id"),
        "status": session.get("status", "UNKNOWN"),
        "events_count": len(session.get("stream_events", [])),
    }
