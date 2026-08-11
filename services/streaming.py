"""
BlendPilot AI — Streaming Orchestrator

Manages real-time UI streaming with WebSocket and SSE support.
Provides message batching, throttling, and graceful connection management.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("blendpilot.services.streaming")


class StreamType(Enum):
    WEBSOCKET = "websocket"
    SSE = "sse"


@dataclass
class ClientConnection:
    """Represents a connected client with its message queue."""
    client_id: str
    stream_type: StreamType
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1000))
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: float = field(default_factory=time.monotonic)
    message_count: int = 0
    throttle_until: float = 0


@dataclass
class StreamMessage:
    """A message to be streamed to clients."""
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message_id: str = field(default_factory=lambda: str(uuid4()))
    priority: int = 0  # Higher priority messages are sent first

    def to_json(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "priority": self.priority,
        }


class StreamingOrchestrator:
    """
    Manages real-time streaming to connected clients with batching and throttling.

    Features:
    - WebSocket and SSE support
    - Message batching (200ms intervals)
    - Throttling (50 msgs/sec when overloaded)
    - Per-client queues with 1000-msg limit
    - Graceful connection failure handling
    """

    def __init__(
        self,
        batch_interval_ms: int = 200,
        throttle_threshold: int = 50,  # msgs per second
        max_queue_size: int = 1000,
        max_clients: int = 5000,
    ):
        self.batch_interval_ms = batch_interval_ms
        self.throttle_threshold = throttle_threshold
        self.max_queue_size = max_queue_size
        self.max_clients = max_clients

        self._connections: Dict[str, ClientConnection] = {}
        self._batch_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        client_id: Optional[str] = None,
        stream_type: StreamType = StreamType.WEBSOCKET,
    ) -> str:
        """Connect a new client and return their client_id."""
        async with self._lock:
            if len(self._connections) >= self.max_clients:
                raise RuntimeError(f"Maximum clients ({self.max_clients}) exceeded")

            client_id = client_id or str(uuid4())

            if client_id in self._connections:
                return client_id

            self._connections[client_id] = ClientConnection(
                client_id=client_id,
                stream_type=stream_type,
            )

            # Start batch task for this client
            self._batch_tasks[client_id] = asyncio.create_task(
                self._batch_and_send(client_id)
            )

            logger.info("Client %s connected via %s", client_id, stream_type.value)
            return client_id

    async def disconnect(self, client_id: str) -> bool:
        """Disconnect a client and clean up resources."""
        async with self._lock:
            if client_id not in self._connections:
                return False

            # Cancel batch task
            if client_id in self._batch_tasks:
                self._batch_tasks[client_id].cancel()
                try:
                    await self._batch_tasks[client_id]
                except asyncio.CancelledError:
                    pass
                del self._batch_tasks[client_id]

            del self._connections[client_id]
            logger.info("Client %s disconnected", client_id)
            return True

    async def broadcast(
        self,
        event_type: str,
        payload: Dict[str, Any],
        priority: int = 0,
        exclude_clients: Optional[List[str]] = None,
    ) -> int:
        """Broadcast a message to all connected clients."""
        count = 0
        exclude = exclude_clients or []

        async with self._lock:
            connections = list(self._connections.items())

        for client_id, connection in connections:
            if client_id in exclude:
                continue

            try:
                message = StreamMessage(
                    event_type=event_type,
                    payload=payload,
                    priority=priority,
                )
                await connection.queue.put(message)
                count += 1
            except asyncio.QueueFull:
                logger.warning(
                    "Queue full for client %s, dropping message", client_id
                )

        return count

    async def broadcast_agent_update(
        self,
        agent_name: str,
        status: str,
        phase: Optional[str] = None,
        progress: Optional[float] = None,
        repair_count: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> int:
        """Broadcast an agent state update to all clients."""
        payload = {
            "agent": agent_name,
            "status": status,
        }
        if phase:
            payload["phase"] = phase
        if progress is not None:
            payload["progress"] = progress
        if repair_count is not None:
            payload["repair_count"] = repair_count
        if reason:
            payload["reason"] = reason

        return await self.broadcast("agent_update", payload, priority=1)

    async def broadcast_status(
        self,
        session_id: str,
        status: str,
        current_agent: Optional[str] = None,
    ) -> int:
        """Broadcast workflow status update."""
        payload = {
            "session_id": session_id,
            "status": status,
        }
        if current_agent:
            payload["current_agent"] = current_agent

        return await self.broadcast("status_update", payload)

    async def broadcast_error(
        self,
        session_id: str,
        error: str,
        agent: Optional[str] = None,
        severity: str = "warning",
    ) -> int:
        """Broadcast an error to all clients."""
        payload = {
            "session_id": session_id,
            "error": error,
            "severity": severity,
        }
        if agent:
            payload["agent"] = agent

        return await self.broadcast("error", payload, priority=2)

    async def _batch_and_send(self, client_id: str) -> None:
        """Batch messages and send to client at intervals."""
        connection = self._connections.get(client_id)
        if not connection:
            return

        batch: List[Dict[str, Any]] = []
        last_batch_time = time.monotonic()
        messages_this_second = 0

        while True:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(
                    connection.queue.get(), timeout=0.1
                )

                current_time = time.monotonic()

                # Check if we need to throttle
                if current_time - last_batch_time >= 1.0:
                    # Reset per-second counter
                    messages_this_second = 0
                    last_batch_time = current_time

                # Check if we've exceeded throttle threshold
                if messages_this_second >= self.throttle_threshold:
                    connection.throttle_until = current_time + 1.0

                if current_time < connection.throttle_until:
                    # Throttled - add to batch
                    batch.append(message.to_json())
                else:
                    # Not throttled - send immediately
                    await self._send_message(client_id, message.to_json())
                    messages_this_second += 1
                    connection.message_count += 1

                # Send batch if full or interval expired
                if (
                    len(batch) >= self.max_queue_size
                    or current_time - last_batch_time >= self.batch_interval_ms / 1000.0
                ):
                    if batch:
                        await self._send_message(client_id, {
                            "event_type": "batch",
                            "messages": batch,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        batch = []
                        last_batch_time = current_time

            except asyncio.QueueEmpty:
                # Send any pending batch
                if batch:
                    await self._send_message(client_id, {
                        "event_type": "batch",
                        "messages": batch,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    batch = []
                    last_batch_time = time.monotonic()

            except asyncio.CancelledError:
                # Send any remaining batch before exiting
                if batch:
                    try:
                        await self._send_message(client_id, {
                            "event_type": "batch",
                            "messages": batch,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                    except Exception:
                        pass
                raise

            except Exception as e:
                logger.error("Error in batch task for client %s: %s", client_id, e)
                break

    async def _send_message(self, client_id: str, message: Dict[str, Any]) -> None:
        """Send a message to a specific client. To be implemented by subclasses."""
        # This method should be overridden by WebSocket/SSE implementations
        pass

    def get_active_connections(self) -> int:
        """Return the number of active client connections."""
        return len(self._connections)

    async def clear_client_queue(self, client_id: str) -> int:
        """Clear all pending messages for a client and return count."""
        connection = self._connections.get(client_id)
        if not connection:
            return 0

        count = 0
        try:
            while True:
                connection.queue.get_nowait()
                count += 1
        except asyncio.QueueEmpty:
            pass

        return count


class WebSocketStreamingOrchestrator(StreamingOrchestrator):
    """WebSocket-specific streaming orchestrator."""

    def __init__(self, send_callback: Callable[[str, Dict[str, Any]], Any]):
        super().__init__()
        self._send_callback = send_callback

    async def _send_message(self, client_id: str, message: Dict[str, Any]) -> None:
        """Send message via WebSocket."""
        try:
            await self._send_callback(client_id, message)
        except Exception as e:
            logger.error("Failed to send to client %s: %s", client_id, e)
            # Remove disconnected client
            await self.disconnect(client_id)


class SSEStreamingOrchestrator(StreamingOrchestrator):
    """SSE-specific streaming orchestrator."""

    def __init__(
        self,
        send_callback: Callable[[str, str], Any],
        sse_event_type: str = "update",
    ):
        super().__init__()
        self._send_callback = send_callback
        self._sse_event_type = sse_event_type

    async def _send_message(self, client_id: str, message: Dict[str, Any]) -> None:
        """Send message via SSE."""
        try:
            message_str = f"event: {self._sse_event_type}\ndata: {message}\n\n"
            await self._send_callback(client_id, message_str)
        except Exception as e:
            logger.error("Failed to send SSE to client %s: %s", client_id, e)
            await self.disconnect(client_id)
