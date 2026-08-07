"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { type ChatMessage } from "@/types/chat";
import { Bot, User, BookOpen, Copy, Check } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Parse RAG sources if present in metadata
  let ragSources: Array<{ title: string; source: string; score: number }> = [];
  if (message.metadata && typeof message.metadata === "object") {
    const meta = message.metadata as Record<string, unknown>;
    if (Array.isArray(meta.ragSources)) {
      ragSources = meta.ragSources as Array<{ title: string; source: string; score: number }>;
    }
  }

  return (
    <div className={`flex gap-3.5 my-4 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-primary text-primary-foreground flex items-center justify-center shrink-0 shadow-sm mt-1">
          <Bot className="w-4 h-4" />
        </div>
      )}

      <div
        className={`relative group max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 text-sm leading-relaxed ${
          isUser
            ? "bg-primary text-primary-foreground rounded-tr-sm shadow-md"
            : "bg-card text-card-foreground border border-border rounded-tl-sm shadow-sm"
        }`}
      >
        {/* RAG citations badges if present */}
        {ragSources.length > 0 && (
          <div className="mb-3 pb-2.5 border-b border-border flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
            <span className="flex items-center gap-1 text-[11px] font-medium text-foreground">
              <BookOpen className="w-3 h-3" />
              Retrieved Context:
            </span>
            {ragSources.map((s, idx) => (
              <Badge
                key={idx}
                variant="outline"
                className="bg-muted text-muted-foreground border-border text-[10px] font-mono py-0 h-5"
              >
                {s.title} ({Math.round(s.score * 100)}%)
              </Badge>
            ))}
          </div>
        )}

        {/* Message content */}
        <div className="prose dark:prose-invert max-w-none text-sm space-y-2 prose-pre:bg-muted prose-pre:border prose-pre:border-border prose-pre:rounded-xl">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Action bar on hover */}
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={handleCopy}
            className="p-1 rounded-md bg-muted text-muted-foreground hover:text-foreground border border-border transition-colors"
            title="Copy message"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-primary" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-xl bg-muted border border-border flex items-center justify-center text-foreground shrink-0 mt-1">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
}
