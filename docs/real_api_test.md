# Real API Test

**request**
```json
{
  "user_prompt": "Create a red wooden table with four legs.",
  "reference_images": [],
  "overrides": {},
  "enable_human_interrupt": false
}
```

**response**
```json
{
  "success": true,
  "project_id": "proj_82738fd7",
  "session_id": "sess_4eb4e427",
  "status": "RUNNING",
  "message": "Modeling workflow started successfully"
}
```

**run_id**
`sess_4eb4e427`

**status changes**
- RUNNING
- COMPLETED
- REVIEW_REQUIRED

**agent/node changes**
- intent_node
- planner_node
- generator_node
- executor_node
- scene_state_node
- render_node
- geometry_qa_node
- geometry_wait_node
- vision_critic_node
- decision_node
- repair_node
- human_review_node

**SceneState**
None (Failed to generate due to backend exception)

**render location/response**
output/table/preview.png

**Geometry QA**
None

**Vision QA**
None

**repair information if triggered**
```json
[
  {
    "plan": null,
    "iteration": 0
  }
]
```

**final result**
REVIEW_REQUIRED

**export information**
URL: http://127.0.0.1:8001/api/export/proj_82738fd7/download
Status Code: 405

---

1. Failure: The real-time stream disconnects prematurely, and the Scene Analysis node crashes.
2. Root cause: `executor_node` sets the overall workflow status to `COMPLETED` prematurely which disconnects the stream. Separately, `node_scene_state` incorrectly tries to `import bpy` directly into the FastAPI process, causing a `ModuleNotFoundError`.
3. File: `graph/nodes.py`
4. Function: `node_execute_blender` and `node_scene_state`
5. Minimum required fix: Remove `"status": "COMPLETED"` from the return dictionary of `node_execute_blender`. Replace the direct Python import of `inspect_scene` in `node_scene_state` with an MCP tool execution (e.g., `mcp_server.execute_tool("inspect_scene")`).
