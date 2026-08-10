export interface WorkflowStreamPayload {
  scene_objects: any;
  event?: string;
  event_id?: number;
  node?: string;
  status?: string;
  session_id?: string;
  state?: Record<string, unknown>;
  error?: string;
}

interface WorkflowStreamOptions {
  sessionId: string;
  onMessage: (payload: WorkflowStreamPayload) => void;
  onOpen?: (transport: "websocket") => void;
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
  onClose,
}: WorkflowStreamOptions): WorkflowStreamHandle {
  let closed = false;
  let socket: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let reconnectAttempts = 0;
  let lastEventId = 0;
  const seenEventIds = new Set<number>();

  const dispatch = (payload: WorkflowStreamPayload) => {
    const eventId = payload.event_id;
    if (typeof eventId === "number" && payload.event !== "ping" && payload.event !== "connected") {
      if (seenEventIds.has(eventId)) return;
      seenEventIds.add(eventId);
      lastEventId = Math.max(lastEventId, eventId);
    }
    
    onMessage(payload);
    
    if (
      payload.event === "workflow_complete" ||
      payload.event === "workflow_missing" ||
      payload.status === "FAILED"
    ) {
      closed = true;
      closeSocket();
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

  const startWebSocket = () => {
    if (closed) return;
    try {
      closeSocket();
      socket = new WebSocket(buildWorkflowWsUrl(sessionId, lastEventId));
    } catch {
      console.error("Failed to construct WebSocket");
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
      onClose?.();
    },
  };
}
