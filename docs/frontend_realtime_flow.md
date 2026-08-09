# Frontend Real-Time Data Flow

Based on a detailed inspection of the existing FastAPI backend (`backend/api/workflow.py`), the following real-time streaming mechanisms are currently implemented:

1. **WebSocket**: Not implemented.
2. **Server-Sent Events (SSE)**: **IMPLEMENTED** (`GET /api/workflow/{session_id}/stream`).
3. **Streaming responses**: Implemented (powers the SSE).
4. **Polling endpoint**: Implemented (`GET /api/workflow/{session_id}/status`).
5. **LangGraph event streaming**: Implemented (wrapped inside the SSE endpoint via `astream`).
6. **Run status endpoint**: Implemented.

## Selected Mechanism: Server-Sent Events (SSE)

Following the priority matrix, **Server-Sent Events (SSE)** is the best existing mechanism. The backend explicitly exposes `stream_workflow_progress(session_id)` to stream LangGraph dictionary updates in real-time. We will use the native browser `EventSource` API.

---

## Detailed Workflow Execution

### 1. User clicks Generate
- **Request**: `POST /api/workflow/start`
- **Payload**: `{"user_prompt": "...", "enable_human_interrupt": true}`
- **Backend**: Generates unique `session_id`, stores initial state in memory, and triggers an `asyncio.create_task` to run the LangGraph asynchronously.

### 2. React receives run_id
- **Response**: `{"success": true, "session_id": "sess_xyz", "project_id": "proj_xyz", "status": "RUNNING"}`
- **React Action**: Frontend saves `session_id` to local state to initiate tracking.

### 3. React tracks run
- **Request**: React opens an SSE connection via `new EventSource('/api/workflow/sess_xyz/stream')`.
- **Response**: The backend holds the HTTP connection open (`text/event-stream`).

### 4. Agent status changes
- **Event**: As LangGraph progresses from node to node (e.g., `intent_node` -> `planner_node`), the backend `astream` generator captures the state mutation.
- **Event Fields**: The backend yields an SSE message formatted as:
  ```json
  data: {
    "session_id": "sess_xyz",
    "node": "planner_node",
    "state": {
      "design_plan": {...},
      "status": "RUNNING"
    }
  }
  ```
- **React Action**: The `useGeneration` hook intercepts `event.data`, parses the JSON, and merges the partial `state` dictionary into the global React state.

### 5. React updates AgentWorkflow
- Because the global React state now reflects `node: "planner_node"`, the `AgentWorkflow` component re-renders, changing the Planning agent's icon from a pending circle to a running spinner, and marking the previous Intent agent as completed.

### 6. Blender executes & QA executes
- The `executor_node`, `scene_state_node`, `geometry_qa_node`, and `vision_critic_node` execute sequentially in the backend.
- Each node pushes its results via SSE (e.g., `state: {"preview_image_path": "...", "scene_summary": {...}}`).
- The React `PreviewPanel`, `GeometryQA`, and `VisionQA` components automatically update as their prop data arrives.

### 7. Repair executes (If required)
- If QA fails, the graph routes to `repair_node`.
- The backend emits an event with `node: "repair_node"` and `state: {"repair_plan": {...}, "iteration_count": 1}`.
- React's `RepairPanel` updates to display the detected problem and the corrective action being taken.

### 8. Final Result & Display
- Once the pipeline satisfies all criteria (or hits the iteration limit), the graph routes to `export_node` or `human_review_node`.
- The final event contains `status: "COMPLETED"` or `status: "REVIEW_REQUIRED"`.
- React displays the final state, activates the Download button, or unlocks the Human Feedback chatbox.

---

## Connection Lifecycle Management

- **Initialization**: Connection is established immediately after a successful `POST /start` response, using `const sse = new EventSource(url)`.
- **Reconnection Behavior**: 
  - The native `EventSource` API handles short-term network drops automatically (it will attempt to reconnect to the stream endpoint).
  - The backend is stateless enough to pick up the stream queue if the client reconnects, though some in-memory queueing exists in `_session_event_queues`.
- **Timeout Behavior**: If the SSE connection remains silent for a prolonged period, or if the server crashes (returning a 50x error on reconnect), the frontend should trigger a fallback `GET /api/workflow/{session_id}/status` poll to check if the session is permanently dead.
- **Cleanup Behavior**: 
  - **Graceful**: The frontend must explicitly call `sse.close()` when it receives an event containing `status: "COMPLETED"`, `status: "FAILED"`, or `status: "REVIEW_REQUIRED"`.
  - **Component Unmount**: The React `useEffect` cleanup function MUST call `sse.close()` to prevent memory leaks and zombie network connections if the user navigates away from the dashboard.
