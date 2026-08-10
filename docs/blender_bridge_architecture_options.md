# Blender Bridge Architecture Analysis

## 1. Current Architecture
- **Launcher:** `scripts/start_blender_bridge.py` starts Blender in `--background` mode.
- **Bridge Server:** `blender_addon/bridge.py` starts a standard Python `HTTPServer` in a `daemon=True` background thread (`_server_thread`).
- **Main Thread:** The main thread blocks using a `while True: time.sleep(1)` loop to prevent Blender from exiting.
- **Command Execution:** Incoming HTTP POST requests are processed directly on the `daemon=True` background thread. The HTTP handler directly invokes `bpy` operations.

## 2. Current Failure
- Rendering a preview (`render_preview`) returns a successful HTTP response but physically fails to write the image file to disk.
- Sometimes context-sensitive operations (`active_object`) fail with `AttributeError` or `KeyError`.

## 3. Root Cause
- **Thread Safety Violation:** Blender's Python API (`bpy`) is explicitly not thread-safe. Arbitrary operations (especially rendering and context manipulation) cannot be reliably executed on a background daemon thread.
- **Blocked Main Thread:** Because the main thread is perpetually blocked in `time.sleep(1)`, Blender's internal C++ job queues and event loops never process. When the background thread triggers `bpy.ops.render.render()`, the operator may succeed in Python, but the underlying C++ render job stalls entirely.

## 4. Option A: Run without `--background`
- **Mechanism:** Remove the `--background` flag, allowing Blender's native GUI event loop to run.
- **Execution:** The daemon thread receives HTTP requests and dispatches them to the main thread using `bpy.app.timers` (which function normally when the GUI is active).
- **Pros:** Native Blender execution; rendering works perfectly.
- **Cons:** Requires a GUI window to be open. Unacceptable for headless server deployments (like Render or Docker environments). 

## 5. Option B: Main-Thread Polling (Recommended)
- **Mechanism:** Keep `--background`. Remove the daemon thread entirely. The HTTP server runs directly on the main Blender Python thread.
- **Execution:** Instead of `server.serve_forever()`, the script enters a loop calling `server.handle_request()` with a small timeout (e.g., `server.timeout = 0.1`). When a request arrives, it is parsed and executed synchronously on the main thread, then the loop continues.
- **Pros:** 100% thread-safe (all `bpy` code runs on the main thread). Rendering works natively and reliably. No need for complex thread communication. Keeps the process alive organically.
- **Cons:** Server processes one request at a time sequentially (which is standard and perfectly fine for a single Blender instance).

## 6. Option C: Dedicated Process Model
- **Mechanism:** Remove the persistent HTTP server entirely. The FastAPI backend invokes a new `blender --background --python-expr "..."` command for every single operation.
- **Pros:** Complete isolation; 100% thread-safe.
- **Cons:** Extremely slow (starting Blender takes seconds per command). Impossible to maintain cheap scene state across operations. Highly inefficient.

## 7. Option D: Native Timers/Event Handlers
- **Mechanism:** Use Blender's native `bpy.app.timers` to dispatch commands from a background HTTP thread to the main thread.
- **Timers Check Results:** **FAILED.** Explicit testing confirms that `bpy.app.timers` **do not execute** in `--background` mode when the main thread is blocked by a Python loop (`time.sleep`). There is no public Python API to manually pump Blender's event loop in background mode.

## 8. Recommended Architecture: Option B (Main-Thread Polling)
We should migrate to **Option B**. The HTTP server must run directly on the main thread, replacing the arbitrary `time.sleep(1)` loop with an HTTP polling loop.

## 9. Why the Recommendation is Safest
Option B eliminates all thread-safety violations by ensuring every `bpy` operation occurs sequentially on the main thread. Because it runs synchronously, operations like `bpy.ops.render.render()` correctly block the thread until the image is physically written to disk, avoiding silent failures. It successfully preserves the `--background` requirement while eliminating the need for broken native timers.

## 10. Exact Files That Would Need Modification
1. **`blender_addon/bridge.py`**:
   - Rewrite `start_bridge_server()` to support a blocking polling mode (e.g., `start_bridge_server_blocking()`).
   - Remove the `daemon=True` thread spawning.
   - Implement:
     ```python
     server.timeout = 0.1
     while True:
         server.handle_request()
     ```
2. **`scripts/start_blender_bridge.py`**:
   - Remove the `time.sleep(1)` loop.
   - Call the new `start_bridge_server_blocking()` directly, which natively keeps the process alive while processing HTTP requests.

## 11. Migration Plan
1. Update `bridge.py` to expose `start_bridge_server_blocking()`.
2. Update `scripts/start_blender_bridge.py` to invoke the blocking server instead of the background thread.
3. Test startup and verify the process remains alive.

## 12. Tests Required After Migration
1. **Health Check:** Verify `127.0.0.1:9876/health` responds immediately.
2. **Execution Context:** Verify `get_scene_summary` correctly reads active objects without thread context errors.
3. **Render Verification:** Run `pytest tests/test_render_pipeline.py` to ensure `preview.png` is physically written to disk.
4. **Validation Test:** Run `pytest tests/test_mcp_server.py` to verify the asset validation tool behaves correctly on the main thread.
