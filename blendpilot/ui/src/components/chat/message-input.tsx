"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ArrowUp, Sparkles, Wand2 } from "lucide-react";

interface MessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

const QUICK_PROMPTS = [
  "📦 Sci-Fi Crate with blue emissive strips (0.6m cube, < 8k tris)",
  "🪵 Red Dining Table with 4 wooden legs (1.4m x 0.8m x 0.75m)",
  "🛢️ Metal Industrial Barrel with yellow hazard stripe",
  "🗡️ Low-Poly Fantasy Sword with steel blade and leather grip",
];

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [content, setContent] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [content]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!content.trim() || disabled) return;
    onSend(content.trim());
    setContent("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="p-4 border-t border-border bg-background/80 backdrop-blur-md">
      {/* Quick Prompt Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 mb-2 scrollbar-none">
        <span className="text-[11px] text-muted-foreground font-medium flex items-center gap-1 shrink-0">
          <Sparkles className="w-3 h-3 text-primary" />
          Templates:
        </span>
        {QUICK_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSend(prompt.replace(/^[^a-zA-Z0-9]+/, ""))}
            disabled={disabled}
            className="px-2.5 py-1 rounded-full bg-muted hover:bg-muted/80 border border-border text-[11px] text-muted-foreground hover:text-foreground shrink-0 transition-colors cursor-pointer"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input Box */}
      <form onSubmit={handleSubmit} className="relative flex items-end gap-2 bg-card border border-input rounded-2xl p-2 shadow-sm transition-colors">
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder="Describe a 3D asset to model, modify, or validate in Blender... (e.g. 'Create a low-poly chest')"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          className="flex-1 max-h-45 bg-transparent border-0 resize-none text-sm text-foreground placeholder:text-muted-foreground focus:outline-none px-3 py-1.5"
        />

        <Button
          type="submit"
          size="icon"
          disabled={!content.trim() || disabled}
          className="h-9 w-9 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 shrink-0 shadow-sm transition-all disabled:opacity-40"
        >
          {disabled ? <Wand2 className="w-4 h-4 animate-spin" /> : <ArrowUp className="w-4 h-4" />}
        </Button>
      </form>
      <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground px-1">
        <span>Press <kbd className="px-1 py-0.5 rounded bg-muted border border-border text-muted-foreground">Enter</kbd> to generate, <kbd className="px-1 py-0.5 rounded bg-muted border border-border text-muted-foreground">Shift + Enter</kbd> for newline</span>
        <span>RAG Context Active</span>
      </div>
    </div>
  );
}
