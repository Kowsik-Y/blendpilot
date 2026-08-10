# Blender Bridge Lifetime Diagnosis

## 1. Exact Reason Blender Exits
Blender exits immediately because it is launched in `--background` (headless) mode and the provided Python script (`--python-expr`) finishes execution. By design, when running in background mode, Blender does not start its infinite GUI event loop; it simply processes all scripts and then cleanly shuts down. As the main Blender process terminates, it abruptly kills the HTTP bridge server thread.

## 2. Exact File/Function Responsible
- **Launcher:** `scripts/start_blender_bridge.py` (in `start_bridge()` where `bootstrap_code` is constructed and executed via `--python-expr`).
- **Server:** `blender_addon/bridge.py` (in `start_bridge_server()`).

## 3. Root Causes
- **Background Mode:** The `--background` flag causes Blender to exit upon script completion.
- **Thread Lifetime:** The HTTP server in `bridge.py` is started as a daemon thread (`daemon=True`). Daemon threads do not prevent a Python process from exiting. Once the main thread (Blender) finishes executing the `bootstrap_code` script, it exits, taking the daemon thread down with it.
- **Missing Blocking Loop:** The `bootstrap_code` has no mechanism (like an infinite loop) to keep the main Python thread alive while the HTTP server listens.
- **Explicit Quit:** There is **no** explicit `sys.exit()`, `quit()`, or `bpy.ops.wm.quit_blender()` causing this. It is a natural process termination.
- **Blender 5.2 Compatibility:** This is **not** a compatibility issue with Blender 5.2. This is expected behavior across all versions of Blender when running background scripts.

## 4. Minimum Required Fix
To prevent Blender from exiting in background mode, the `bootstrap_code` in `scripts/start_blender_bridge.py` must block the main thread indefinitely so the daemon thread can continue running. 

The minimum fix is adding a `time.sleep` loop to the end of `bootstrap_code`, but *only* if running in background mode (so we don't freeze the UI in GUI mode):

```python
import bpy, time
if bpy.app.background:
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
```

## 5. Can Blender 5.2 continue to be used?
**Yes.** Once the script lifetime bug is fixed, Blender 5.2 is fully compatible with the existing HTTP bridge server. The bridge does not rely on any deprecated APIs that would prevent it from functioning in 5.2.
