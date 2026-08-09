# Frontend Integration Contract

This document maps all required frontend UI operations to the exact existing BlendPilot FastAPI backend endpoints, defining the data flow and required state architecture.

## API Mapping

### 1. Generate Model
- **React function name**: `generateModel(prompt, overrides)`
- **HTTP method**: `POST`
- **Exact endpoint**: `/api/workflow/start`
- **Request parameters/body**: 
  ```json
  {
    "user_prompt": "string",
    "reference_images": [],
    "overrides": {},
    "enable_human_interrupt": false
  }
  ```
- **Response structure**: 
  ```json
  {
    "success": true,
    "project_id": "string",
    "session_id": "string",
    "status": "string",
    "message": "string"
  }
  ```
- **Error response**: `422 Unprocessable Entity`
- **Synchronous/Asynchronous**: Asynchronous
- **Polling/WebSocket/SSE requirement**: None (Trigger)
- **React component**: `PromptPanel`

### 2. Track Generation Run
- **React function name**: `connectEventStream(sessionId)`
- **HTTP method**: `GET`
- **Exact endpoint**: `/api/workflow/{session_id}/stream`
- **Request parameters/body**: None
- **Response structure**: `text/event-stream` yielding JSON objects:
  ```json
  data: {"event": "snapshot", "state": {...}}
  data: {"session_id": "...", "node": "...", "state": {...}}
  ```
- **Error response**: `404 Not Found`
- **Synchronous/Asynchronous**: Asynchronous
- **Polling/WebSocket/SSE requirement**: SSE requirement
- **React component**: `useGeneration` Hook

### 3. Get Current Agent/Node
- **Resolved via**: Track Generation Run (SSE)
- **Data Source**: `node` (current LangGraph node) and `state.current_agent` extracted directly from the SSE event payload.
- **React component**: `AgentWorkflow`

### 4. Get SceneState
- **Resolved via**: Track Generation Run (SSE)
- **Data Source**: `state.scene_summary` pushed via the SSE payload when the `scene_state_node` finishes.
- **React component**: `SceneObjects`

### 5. Get Render
- **React function name**: `getRenderUrl(projectId)`
- **HTTP method**: `GET`
- **Exact endpoint**: `/static/{project_id}/preview.png`
- **Request parameters/body**: None
- **Response structure**: `image/png`
- **Error response**: `404 Not Found`
- **Synchronous/Asynchronous**: Synchronous (Browser `<img>` rendering)
- **Polling/WebSocket/SSE requirement**: None
- **React component**: `PreviewPanel`

### 6. Get Geometry Validation
- **Resolved via**: Track Generation Run (SSE)
- **Data Source**: `state.validation_report` pushed via the SSE payload.
- **React component**: `GeometryQA`

### 7. Get Vision Validation
- **Resolved via**: Track Generation Run (SSE)
- **Data Source**: `state.vision_report` pushed via the SSE payload.
- **React component**: `VisionQA`

### 8. Get Repair Status
- **Resolved via**: Track Generation Run (SSE)
- **Data Source**: `state.repair_plan` and `state.iteration_count` pushed via the SSE payload.
- **React component**: `RepairPanel`

### 9. Submit Human Feedback
- **React function name**: `submitFeedback(sessionId, action, text)`
- **HTTP method**: `POST`
- **Exact endpoint**: `/api/workflow/{session_id}/feedback`
- **Request parameters/body**: 
  ```json
  {
    "action": "APPROVE",
    "feedback_text": "string"
  }
  ```
- **Response structure**: 
  ```json
  {
    "success": true,
    "session_id": "string",
    "action": "string",
    "message": "string"
  }
  ```
- **Error response**: `404 Not Found`
- **Synchronous/Asynchronous**: Asynchronous
- **Polling/WebSocket/SSE requirement**: None (Trigger)
- **React component**: `FeedbackInput`

### 10. Export Asset
- **React function name**: `getExportUrl(projectId)`
- **HTTP method**: `GET`
- **Exact endpoint**: `/api/export/{project_id}/download`
- **Request parameters/body**: None
- **Response structure**: `application/zip` (Triggers browser download)
- **Error response**: `404 Not Found`
- **Synchronous/Asynchronous**: Synchronous (Browser `window.location.href`)
- **Polling/WebSocket/SSE requirement**: None
- **React component**: `PreviewPanel` (Export Controls)

---

## Frontend Data Flow

```text
PromptPanel
    ↓ (Start Workflow)
useGeneration
    ↓ (Invokes generateModel)
api.js
    ↓ (POST /api/workflow/start)
FastAPI
    ↓ (Triggers graph)
LangGraph
```
*Note: Once started, `useGeneration` immediately connects to the SSE stream and distributes the real-time state downwards to all visualization components.*

---

## Frontend Required State (Generation Run)

```javascript
{
    runId: "sess_123456",
    projectId: "proj_123456",
    prompt: "Create a red table...",
    status: "RUNNING", // IDLE, RUNNING, REVIEW_REQUIRED, COMPLETED, FAILED
    currentAgent: "Generation Agent",
    currentNode: "generator_node",
    iteration: 1,
    maxIterations: 3,
    sceneState: { ... }, // Mapped from scene_summary
    render: "/static/proj_123456/preview.png",
    geometryQA: { passed: false, checks: [...] },
    visionQA: { overall_result: "REPAIR REQUIRED", ... },
    repair: { problem: "Missing leg", corrective_operation: "...", affected_object: "..." },
    activityLog: [
      { time: "18:32:01", agent: "Intent Agent", msg: "State updated..." }
    ],
    error: null
}
```

---

## Missing Backend Information

Based strictly on inspecting the existing backend, the following data required by the UI design is currently **NOT** provided by the backend:

1. **`maxIterations` variable**: The backend hardcodes the maximum repair limit (3) inside the `route_after_decision` routing function. The LangGraph state does not export `max_iterations`, meaning the UI cannot dynamically render "Repair attempt: 1 / 3" without hardcoding `3` on the frontend.
2. **Activity Log Timestamps**: The agents and SSE stream do not emit explicit timestamps. To populate the `18:32:01` column in the Activity Log, the frontend will have to generate client-side `Date.now()` timestamps at the exact moment an SSE event arrives.
3. **Explicit Agent Log Messages**: The SSE stream pushes raw `state` dictionary diffs (e.g., `{"node": "planner_node", "state": {"design_plan": {...}}}`). It does not emit human-readable terminal messages (e.g., `"8-step modeling plan created."`). The frontend will have to artificially construct these log messages based on which node just triggered.
