"use client";

import { useEffect, useRef, useState } from "react";
import { type ChatMessage } from "@/types/chat";
import { MessageBubble } from "./message-bubble";
import { MessageInput } from "./message-input";
import { AgentProgress, type ProgressStep } from "./agent-progress";
import { Box, Sparkles } from "lucide-react";
import { toast } from "sonner";

interface ChatInterfaceProps {
  sessionId: string;
  initialMessages?: ChatMessage[];
}

export function ChatInterface({ sessionId, initialMessages = [] }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [activeRagSources, setActiveRagSources] = useState<Array<{ title: string; source: string; score: number }>>([]);
  const [agentSteps, setAgentSteps] = useState<ProgressStep[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || streaming) return;

    // Add optimistic user message
    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      sessionId,
      role: "user",
      content,
      tokenCount: Math.ceil(content.length / 4),
      createdAt: new Date(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setStreaming(true);
    setStreamingContent("");
    setActiveRagSources([]);

    // Initialize agent progress visualization
    setAgentSteps([
      { id: "1", name: "1. Intent Parser", status: "running", detail: "Analyzing design parameters..." },
      { id: "2", name: "2. Scene Scanner", status: "pending" },
      { id: "3", name: "3. Planning Agent", status: "pending" },
      { id: "4", name: "4. Modeling Execution", status: "pending" },
      { id: "5", name: "5. Material Applier", status: "pending" },
      { id: "6", name: "6. QA & Topology", status: "pending" },
    ]);

    try {
      const response = await fetch(`/api/chat/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || "Failed to send message");
      }

      // Read SSE stream
      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let accumulated = "";

      // Simulate step progression
      setTimeout(() => {
        setAgentSteps((prev) =>
          prev.map((s) =>
            s.id === "1" ? { ...s, status: "done" } : s.id === "2" ? { ...s, status: "done" } : s.id === "3" ? { ...s, status: "running" } : s
          )
        );
      }, 1200);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split("\n\n").filter(Boolean);

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const jsonStr = line.replace(/^data: /, "").trim();
          if (!jsonStr) continue;

          try {
            const data = JSON.parse(jsonStr);

            if (data.type === "rag_sources") {
              setActiveRagSources(data.sources);
            } else if (data.type === "chunk") {
              accumulated += data.content;
              setStreamingContent(accumulated);
            } else if (data.type === "error") {
              toast.error(data.error);
            } else if (data.type === "done") {
              setAgentSteps((prev) => prev.map((s) => ({ ...s, status: "done" })));
            }
          } catch {
            // Ignore parse errors
          }
        }
      }

      // Add final assistant message
      if (accumulated) {
        const assistantMsg: ChatMessage = {
          id: `msg-${Date.now()}`,
          sessionId,
          role: "assistant",
          content: accumulated,
          metadata: { ragSources: activeRagSources },
          tokenCount: Math.ceil(accumulated.length / 4),
          createdAt: new Date(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error generating response";
      toast.error(msg);
    } finally {
      setStreaming(false);
      setStreamingContent("");
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] bg-background text-foreground">
      {/* Messages Scroll Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-4">
        {messages.length === 0 && !streaming && (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto py-12">
            <div className="p-4 rounded-3xl bg-muted border border-border text-foreground mb-4 shadow-sm">
              <Box className="w-12 h-12" />
            </div>
            <h2 className="text-2xl font-bold text-foreground tracking-tight mb-2">
              What 3D asset would you like to build?
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed mb-6">
              BlendPilot converts natural language descriptions into game-ready Blender assets with verified topology, PBR materials, and real-time QA.
            </p>
            <div className="flex items-center gap-2 text-xs text-foreground bg-muted px-3.5 py-1.5 rounded-full border border-border">
              <Sparkles className="w-3.5 h-3.5 text-primary" />
              <span>RAG Knowledge Base & Blender Docs Connected</span>
            </div>
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}

        {/* Live streaming message */}
        {streaming && (
          <div>
            <AgentProgress steps={agentSteps} />
            <MessageBubble
              message={{
                id: "streaming",
                sessionId,
                role: "assistant",
                content: streamingContent || "_Analyzing Blender design context..._",
                metadata: { ragSources: activeRagSources },
                tokenCount: 0,
                createdAt: new Date(),
              }}
            />
          </div>
        )}
      </div>

      {/* Message Input Bar */}
      <MessageInput onSend={handleSendMessage} disabled={streaming} />
    </div>
  );
}
