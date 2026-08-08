export interface WorkflowStreamPayload {
  event?: string;
  event_id?: number;
  node?: string;
  status?: string;
  session_id?: string;
  step_id?: number;
  total_steps?: number;
  step_count?: number;
  description?: string;
  tool?: string;
  error?: string;
  reasoning?: string;
  parameters?: Record<string, unknown>;
  response?: Record<string, unknown>;
  state?: Record<string, unknown>;
}

interface WorkflowStreamOptions {
  sessionId: string;
  onMessage: (payload: WorkflowStreamPayload) => void;
  onOpen?: (transport: "websocket" | "sse") => void;
  onFallback?: () => void;
  onClose?: () => void;
}

interface WorkflowStreamHandle {
  close: () => void;
}

const directBackendWsBase =
  process.env.NEXT_PUBLIC_BACKEND_WS_URL ||
  process.env.NEXT_PUBLIC_BACKEND_API_URL?.replace(/^http/, "ws") ||
  "ws://127.0.0.1:8000";

function buildWorkflowWsUrl(sessionId: string, lastEventId: number) {
  const url = new URL(`/api/workflow/${sessionId}/ws`, directBackendWsBase);
  if (lastEventId > 0) {
    url.searchParams.set("after", String(lastEventId));
  }
  return url.toString();
}

export function connectWorkflowStream({
  sessionId,
  onMessage,
  onOpen,
  onFallback,
  onClose,
}: WorkflowStreamOptions): WorkflowStreamHandle {
  let closed = false;
  let socket: WebSocket | null = null;
  let eventSource: EventSource | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let reconnectAttempts = 0;
  let lastEventId = 0;
  const seenEventIds = new Set<number>();

  const dispatch = (payload: WorkflowStreamPayload) => {
    const eventId = payload.event_id;
    if (typeof eventId === "number" && payload.event !== "snapshot" && payload.event !== "ping") {
      if (seenEventIds.has(eventId)) return;
      seenEventIds.add(eventId);
      lastEventId = Math.max(lastEventId, eventId);
    }
    onMessage(payload);
    if (
      payload.event === "workflow_complete" ||
      payload.event === "workflow_missing" ||
      (payload.status === "FAILED" && payload.event !== "tool_result")
    ) {
      closed = true;
      closeSocket();
      eventSource?.close();
      onClose?.();
    }
  };

  const closeSocket = () => {
    if (socket) {
      socket.onopen = null;
      socket.onmessage = null;
      socket.onerror = null;
      socket.onclose = null;
      socket.close();
      socket = null;
    }
  };

  const startSseFallback = () => {
    if (closed || eventSource) return;
    closeSocket();
    onFallback?.();
    eventSource = new EventSource(`/api/pipeline/${sessionId}/stream`);
    eventSource.onopen = () => onOpen?.("sse");
    eventSource.onmessage = (event) => {
      try {
        dispatch(JSON.parse(event.data) as WorkflowStreamPayload);
      } catch {
        // Ignore malformed stream frames.
      }
    };
    eventSource.onerror = () => {
      eventSource?.close();
      eventSource = null;
      if (!closed) {
        reconnectTimer = setTimeout(startWebSocket, 1500);
      }
    };
  };

  const startWebSocket = () => {
    if (closed) return;
    try {
      closeSocket();
      socket = new WebSocket(buildWorkflowWsUrl(sessionId, lastEventId));
    } catch {
      startSseFallback();
      return;
    }

    socket.onopen = () => {
      reconnectAttempts = 0;
      onOpen?.("websocket");
    };

    socket.onmessage = (event) => {
      try {
        dispatch(JSON.parse(event.data) as WorkflowStreamPayload);
      } catch {
        // Ignore malformed stream frames.
      }
    };

    socket.onerror = () => {
      socket?.close();
    };

    socket.onclose = (event) => {
      closeSocket();
      if (closed || event.code === 4404) return;
      reconnectAttempts += 1;
      if (reconnectAttempts >= 3) {
        startSseFallback();
        return;
      }
      const delay = Math.min(5000, 500 * 2 ** (reconnectAttempts - 1));
      reconnectTimer = setTimeout(startWebSocket, delay);
    };
  };

  startWebSocket();

  return {
    close: () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      closeSocket();
      eventSource?.close();
      onClose?.();
    },
  };
}
