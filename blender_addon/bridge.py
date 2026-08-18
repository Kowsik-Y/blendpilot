"""
BlendPilot — Blender Bridge Server

An HTTP server running inside Blender that receives JSON commands
from external clients (BlenderClient) and executes them via the
operator registry.

Architecture:
    External Python (BlenderClient)
        → HTTP POST to localhost:9876/execute
        → Bridge validates the command
        → Queues it for execution on Blender's main thread
        → Core function runs via bpy.app.timers
        → Response returned to client

Security:
    - Binds ONLY to 127.0.0.1 (localhost)
    - Command whitelist — only registered commands execute
    - No shell access, no exec(), no arbitrary code execution
    - Input validation via Pydantic schemas
    - 30-second timeout per command
"""

from __future__ import annotations

import json
import logging
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

logger = logging.getLogger("blendpilot.addon.bridge")

# Global state
_server: HTTPServer | None = None
_server_thread: threading.Thread | None = None
_start_time: float = 0.0
_commands_processed: int = 0


def _run_on_blender_main_thread(handler: Any, parameters: dict[str, Any], timeout: float = 30.0) -> dict[str, Any]:
    """Run a bridge handler through Blender's timer queue and wait for its result.

    HTTP handlers run on the bridge server thread. Blender's data API and
    operators must instead run on Blender's main thread; using them directly
    from the HTTP thread produces incomplete ``bpy.context`` objects.
    """
    import bpy  # type: ignore[import-not-found]

    completed = threading.Event()
    outcome: dict[str, Any] = {}

    def invoke() -> None:
        try:
            outcome["result"] = handler(parameters)
        except BaseException as error:
            outcome["error"] = error
            outcome["traceback"] = traceback.format_exc()
        finally:
            completed.set()
        return None

    bpy.app.timers.register(invoke, first_interval=0.0)
    if not completed.wait(timeout):
        raise TimeoutError(
            f"Blender did not execute the command within {timeout:.0f} seconds.")
    if "error" in outcome:
        error = outcome["error"]
        logger.error("Blender command failed on main thread:\n%s",
                     outcome.get("traceback", ""))
        raise error
    return outcome.get("result", {})


class BridgeRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Blender bridge.

    Endpoints:
        GET  /health   — Server health check
        POST /execute  — Execute a bridge command
        GET  /commands — List available commands
    """

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/commands":
            self._handle_list_commands()
        else:
            self._send_json(404, {"error": f"Not found: {self.path}"})

    def do_POST(self) -> None:
        """Handle POST requests."""
        if self.path == "/execute":
            self._handle_execute()
        else:
            self._send_json(404, {"error": f"Not found: {self.path}"})

    def _handle_health(self) -> None:
        """Return server health status."""
        global _start_time, _commands_processed

        try:
            import bpy  # type: ignore[import-not-found]
            blender_version = ".".join(str(v) for v in bpy.app.version)
        except ImportError:
            blender_version = "unknown"

        self._send_json(200, {
            "status": "ok",
            "blender_version": blender_version,
            "addon_version": "0.1.0",
            "uptime_seconds": round(time.time() - _start_time, 1),
            "commands_processed": _commands_processed,
        })

    def _handle_list_commands(self) -> None:
        """Return list of available commands."""
        from blender_addon.operators import list_commands

        self._send_json(200, {
            "commands": list_commands(),
            "count": len(list_commands()),
        })

    def _handle_execute(self) -> None:
        """Execute a bridge command."""
        global _commands_processed

        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._send_json(400, {
                "request_id": "",
                "success": False,
                "error": "Empty request body.",
            })
            return

        raw_body = self.rfile.read(content_length)

        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError as e:
            self._send_json(400, {
                "request_id": "",
                "success": False,
                "error": f"Invalid JSON: {e}",
            })
            return

        # Validate command structure
        command_name = body.get("command", "")
        request_id = body.get("request_id", f"req_{int(time.time())}")
        parameters = body.get("parameters", {})

        if not command_name:
            self._send_json(400, {
                "request_id": request_id,
                "success": False,
                "error": "Missing 'command' field.",
            })
            return

        # Look up handler
        from blender_addon.operators import get_handler

        handler = get_handler(command_name)
        if handler is None:
            from blender_addon.operators import list_commands
            self._send_json(400, {
                "request_id": request_id,
                "success": False,
                "error": (
                    f"Unknown command: '{command_name}'. "
                    f"Available commands: {list_commands()}"
                ),
            })
            return

        # Execute the command
        start = time.perf_counter()
        try:
            logger.info("Executing command: %s (id=%s)",
                        command_name, request_id)
            result = _run_on_blender_main_thread(handler, parameters)
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            _commands_processed += 1
            logger.info(
                "Command %s completed in %.1fms (id=%s)",
                command_name, elapsed_ms, request_id,
            )

            self._send_json(200, {
                "request_id": request_id,
                "success": True,
                "result": result,
                "error": None,
                "execution_time_ms": round(elapsed_ms, 2),
            })

        except (ValueError, TypeError, KeyError) as e:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            logger.warning(
                "Command %s failed (validation): %s (id=%s)",
                command_name, e, request_id,
            )
            self._send_json(400, {
                "request_id": request_id,
                "success": False,
                "error": str(e),
                "execution_time_ms": round(elapsed_ms, 2),
            })

        except FileNotFoundError as e:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            logger.warning(
                "Command %s failed (not found): %s (id=%s)",
                command_name, e, request_id,
            )
            self._send_json(404, {
                "request_id": request_id,
                "success": False,
                "error": str(e),
                "execution_time_ms": round(elapsed_ms, 2),
            })

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            logger.error(
                "Command %s failed (internal): %s\n%s",
                command_name, e, traceback.format_exc(),
            )
            self._send_json(500, {
                "request_id": request_id,
                "success": False,
                "error": f"Internal error: {e}",
                "execution_time_ms": round(elapsed_ms, 2),
            })

    def _send_json(self, status_code: int, data: dict[str, Any]) -> None:
        """Send a JSON response."""
        response_body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format: str, *args: Any) -> None:
        """Redirect HTTP logs to our logger instead of stderr."""
        logger.debug("HTTP %s", format % args)


def start_bridge_server(host: str = "127.0.0.1", port: int = 9876) -> None:
    """Start the bridge HTTP server in a background thread.

    Args:
        host: Bind address (MUST be 127.0.0.1 for security).
        port: Port number to listen on.

    Raises:
        RuntimeError: If the server is already running.
    """
    global _server, _server_thread, _start_time

    if _server is not None:
        raise RuntimeError("Bridge server is already running.")

    if host != "127.0.0.1":
        logger.warning(
            "Security: Forcing bridge server to bind to 127.0.0.1 "
            "(requested: %s)", host,
        )
        host = "127.0.0.1"

    # Register all operator handlers
    from blender_addon.operators import register_all_operators
    register_all_operators()

    _server = HTTPServer((host, port), BridgeRequestHandler)
    _start_time = time.time()

    _server_thread = threading.Thread(
        target=_server.serve_forever,
        name="BlendPilotBridge",
        daemon=True,
    )
    _server_thread.start()

    logger.info("Bridge server started on http://%s:%d", host, port)


def stop_bridge_server() -> None:
    """Stop the bridge HTTP server."""
    global _server, _server_thread

    if _server is not None:
        _server.shutdown()
        _server.server_close()
        _server = None
        logger.info("Bridge server stopped.")

    if _server_thread is not None:
        _server_thread.join(timeout=5.0)
        _server_thread = None


def is_running() -> bool:
    """Check if the bridge server is currently running."""
    return _server is not None
