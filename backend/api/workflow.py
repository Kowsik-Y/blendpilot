"""
BlendPilot AI — Workflow API Endpoints

Provides endpoints for launching autonomous modeling workflows, streaming SSE events,
submitting human-in-the-loop feedback, and inspecting session status.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from graph.graph import build_blendpilot_graph
from graph.persistence import get_checkpointer
from graph.state import BlendPilotState, create_initial_state

logger = logging.getLogger("blendpilot.api.workflow")

router = APIRouter(prefix="/api/workflow", tags=["Workflow"])

# In-memory session registry and event queues for active streams
_active_sessions: dict[str, dict[str, Any]] = {}
_session_event_queues: dict[str, list[asyncio.Queue]] = {}
_global_checkpointer = get_checkpointer()
_compiled_app = build_blendpilot_graph(enable_human_interrupt=True, checkpointer=_global_checkpointer)


class StartWorkflowRequest(BaseModel):
    """Payload to initiate a 3D modeling workflow."""
    user_prompt: str = Field(..., min_length=3, description="Natural-language description of the 3D asset")
    reference_images: list[str] = Field(default_factory=list, description="Base64 or URLs to reference images")
    overrides: dict[str, Any] | None = Field(default=None, description="Optional manual parameter overrides")
    enable_human_interrupt: bool = Field(default=False, description="Whether to pause at human feedback stage")


class HumanFeedbackRequest(BaseModel):
    """Payload for human reviewer decisions."""
    action: str = Field(default="APPROVE", description="APPROVE, REQUEST_CHANGE, ROLLBACK, REJECT")
    feedback_text: str | None = Field(default=None, description="Detailed revision comments")


@router.post("/start")
async def start_workflow(request: StartWorkflowRequest) -> dict[str, Any]:
    """Initiate a new 10-workflow agentic modeling pipeline."""
    project_id = f"proj_{uuid.uuid4().hex[:8]}"
    session_id = f"sess_{uuid.uuid4().hex[:8]}"

    initial_state = create_initial_state(
        user_prompt=request.user_prompt,
        project_id=project_id,
        session_id=session_id,
        reference_images=request.reference_images,
        overrides=request.overrides,
    )

    _active_sessions[session_id] = {
        "state": initial_state,
        "status": "RUNNING",
        "thread_id": session_id,
    }
    _session_event_queues[session_id] = []

    # Run execution in background task
    asyncio.create_task(_run_workflow_task(session_id, initial_state))

    return {
        "success": True,
        "project_id": project_id,
        "session_id": session_id,
        "status": "RUNNING",
        "message": "Modeling workflow started successfully",
    }


async def _run_workflow_task(session_id: str, state: BlendPilotState) -> None:
    """Execute the StateGraph and dispatch SSE events to listeners."""
    config = {"configurable": {"thread_id": session_id}}
    try:
        async for output in _compiled_app.astream(state, config=config):
            # output is {node_name: partial_state}
            for node_name, partial_state in output.items():
                if session_id in _active_sessions:
                    _active_sessions[session_id]["state"].update(partial_state)
                    current_agent = partial_state.get("current_agent", node_name)
                    _active_sessions[session_id]["status"] = partial_state.get("status", "RUNNING")

                # Dispatch SSE event
                event_payload = {
                    "session_id": session_id,
                    "node": node_name,
                    "state": partial_state,
                }
                await _broadcast_event(session_id, event_payload)

        if session_id in _active_sessions:
            current_status = _active_sessions[session_id]["state"].get("status", "COMPLETED")
            _active_sessions[session_id]["status"] = current_status

    except Exception as e:
        logger.exception("Workflow error in session %s: %s", session_id, e)
        if session_id in _active_sessions:
            _active_sessions[session_id]["status"] = "FAILED"
            _active_sessions[session_id]["state"]["error"] = str(e)
        await _broadcast_event(session_id, {"session_id": session_id, "error": str(e), "status": "FAILED"})


async def _broadcast_event(session_id: str, payload: dict[str, Any]) -> None:
    """Send event to all active SSE queues for this session."""
    queues = _session_event_queues.get(session_id, [])
    for q in queues:
        await q.put(payload)


@router.get("/{session_id}/stream")
async def stream_workflow_progress(session_id: str) -> StreamingResponse:
    """Stream real-time Server-Sent Events (SSE) for workflow progress."""
    if session_id not in _active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    queue: asyncio.Queue = asyncio.Queue()
    if session_id not in _session_event_queues:
        _session_event_queues[session_id] = []
    _session_event_queues[session_id].append(queue)

    async def event_generator() -> AsyncGenerator[str, None]:
        # Send current state snapshot immediately
        current_state = _active_sessions[session_id]["state"]
        yield f"data: {json.dumps({'event': 'snapshot', 'state': current_state})}\n\n"

        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("status") in ["COMPLETED", "FAILED"]:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if session_id in _session_event_queues and queue in _session_event_queues[session_id]:
                _session_event_queues[session_id].remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/{session_id}/feedback")
async def submit_human_feedback(session_id: str, request: HumanFeedbackRequest) -> dict[str, Any]:
    """Submit human review decision to resume an interrupted workflow."""
    if session_id not in _active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data = _active_sessions[session_id]
    session_data["state"]["human_action"] = request.action
    session_data["state"]["human_feedback"] = request.feedback_text

    config = {"configurable": {"thread_id": session_id}}

    # Resume the graph
    asyncio.create_task(_run_workflow_task(session_id, session_data["state"]))

    return {
        "success": True,
        "session_id": session_id,
        "action": request.action,
        "message": f"Human feedback '{request.action}' applied. Workflow resuming.",
    }


@router.get("/{session_id}/status")
async def get_session_status(session_id: str) -> dict[str, Any]:
    """Get the current state and execution status of a session."""
    if session_id not in _active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data = _active_sessions[session_id]
    state = session_data["state"]

    return {
        "session_id": session_id,
        "project_id": state.get("project_id"),
        "status": session_data.get("status", "UNKNOWN"),
        "current_agent": state.get("current_agent"),
        "design_spec": state.get("design_spec"),
        "preview_image_path": state.get("preview_image_path"),
        "exported_files": state.get("exported_files", []),
        "asset_report": state.get("asset_report"),
        "events_count": len(state.get("events", [])),
    }
