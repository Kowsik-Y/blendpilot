# Real Executor Agent Test

This document tracks the resolution of the silent-mock failure in the LangGraph `executor_node`.

## Previous Behavior
The `node_executor` function relied on `try: import bpy` to determine if it was running inside Blender. Because the FastAPI backend and LangGraph agents run in an external Python process, `bpy` is never available. This triggered an `ImportError`, hardcoding `mock_mode = True`. As a result, the `GenerationAgent` mocked all executions and bypassed the `BlenderClient`, even though a live Blender instance was actively running and listening at `127.0.0.1:9876`.

## New Behavior
The hardcoded `import bpy` block was completely removed from `node_executor`.
The `mock_mode` flag passed to the `GenerationAgent` is now strictly derived from the graph state:
```python
mock_mode = state.get("baseline_mode", False)
```
If `baseline_mode` is `False`, the agent sends real HTTP POST requests to the `BlenderClient`. Furthermore, the `BlenderClient` was updated to remove its silent fallback logic. If `mock_mode` is `False` but the bridge is unreachable, it raises a strict `RuntimeError`.

## Real Execution Result
**Prompt:** "Create a red wooden table with four legs."
- The executor correctly stayed in real mode.
- LangGraph generated Blender python operations via the LLM.
- The `GenerationAgent` sent the operations to `http://127.0.0.1:9876/execute`.
- The Blender bridge physically executed the commands and returned success.

## Blender Object Count
Querying the real Blender bridge (`get_scene_summary`) confirms the objects were successfully created in the 3D scene:
- **Object Count**: 11 (including cameras, lights, and generated meshes)
- **Generated Objects**: `table`, `leg`, `table.001`, `leg.001`
- **Result**: PASS

## Simulation Test Result
When running the workflow with `baseline_mode = True`, the system successfully routes to the simulation branch. The generator logs mock execution details, bypassing the Blender bridge safely as intended.

## Remaining Issues
The LangGraph pipeline successfully reached the Vision QA stage, but failed at the `VisionCriticAgent`. The `llama-3.2-90b-vision-preview` LLM running via `ChatGroq` threw a `400` error:
`{'message': 'messages[0].content must be a string'}`
This indicates an API mismatch between LangChain's vision message arrays and Groq's expected input structure. This is the next target for resolution.
