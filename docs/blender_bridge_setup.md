# Blender Bridge Setup

This document outlines the startup requirements and configuration for the background Blender Bridge process used by BlendPilot.

## 1. Network Configuration
- **Port:** `9876`
- **Host:** `127.0.0.1` (Localhost only)

## 2. Execution Model
- **Continuous Execution:** The bridge must remain running continuously in the background. It acts as a long-lived HTTP server running inside a single Blender process. The FastAPI backend sends individual commands to this long-lived process rather than starting Blender from scratch for every command.
- **FastAPI Connection:** FastAPI (via `BlenderClient`) connects to the bridge using synchronous or asynchronous HTTP POST requests to `http://127.0.0.1:9876/execute`. The request body is JSON containing the command payload.

## 3. Environment & Compatibility
- **Environment Variables:** You can set the `BLENDER_PATH` environment variable if your Blender executable is in a non-standard location. Otherwise, the script attempts to find it automatically in standard OS locations or via the system `PATH`.
- **Blender 4.x Support:** Yes, the bridge relies on standard `bpy` module commands that are fully compatible with Blender 4.x. 

## 4. Startup Commands

**Windows & Headless Execution:**
The bridge launcher defaults to headless (background) execution automatically. Run the following command from the project root:

```bash
python scripts/start_blender_bridge.py
```

If you ever need to run it in a visible GUI mode for debugging:
```bash
python scripts/start_blender_bridge.py --gui
```

## 5. Verification & Health Checks

**How to verify the bridge is ready:**
You can verify the bridge is running and ready to accept commands by sending an HTTP GET request to the health endpoint:
```text
GET http://127.0.0.1:9876/health
```

**Successful Connection Response:**
A successful connection to the health endpoint will return an HTTP 200 response with a JSON payload similar to:
```json
{
    "status": "ok",
    "blender_version": "4.x.x",
    "addon_version": "0.1.0",
    "uptime_seconds": 12.5,
    "commands_processed": 0
}
```
