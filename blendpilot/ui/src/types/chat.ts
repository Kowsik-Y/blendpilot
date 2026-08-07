export interface ChatMessage {
  id: string;
  sessionId: string;
  role: "user" | "assistant" | "system";
  content: string;
  metadata?: Record<string, unknown>;
  tokenCount: number;
  createdAt: Date;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messageCount?: number;
}

export interface AgentStep {
  step: string;
  status: "pending" | "running" | "done" | "failed";
  detail?: string;
}
