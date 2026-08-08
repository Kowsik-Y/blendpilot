"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  PromptInput,
  PromptInputAction,
  PromptInputActionGroup,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/nexus-ui/prompt-input";
import { ArrowUp, LoaderCircle, Paperclip, Sparkles } from "lucide-react";

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

  const handleSubmit = (value = content) => {
    if (!value.trim() || disabled) return;
    onSend(value.trim());
    setContent("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  return (
    <div className="border-t border-border bg-background/80 p-4 backdrop-blur-md">
      {/* Quick Prompt Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 mb-2 scrollbar-none">
        <span className="text-[11px] text-muted-foreground font-medium flex items-center gap-1 shrink-0">
          <Sparkles className="w-3 h-3 text-primary" />
          Templates:
        </span>
        {QUICK_PROMPTS.map((prompt, idx) => (
          <Button
            key={idx}
            type="button"
            onClick={() => onSend(prompt.replace(/^[^a-zA-Z0-9]+/, ""))}
            disabled={disabled}
            variant="outline"
            size="xs"
            className="shrink-0 rounded-full"
          >
            {prompt}
          </Button>
        ))}
      </div>

      <PromptInput onSubmit={handleSubmit}>
        <PromptInputTextarea
          ref={textareaRef}
          placeholder="Describe a 3D asset to model, modify, or validate in Blender... (e.g. 'Create a low-poly chest')"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          disabled={disabled}
        />
        <PromptInputActions>
          <PromptInputActionGroup>
            <PromptInputAction asChild>
              <Button type="button" variant="ghost" size="icon-sm" disabled={disabled} aria-label="Add attachment">
                <Paperclip />
              </Button>
            </PromptInputAction>
            <span className="text-xs text-muted-foreground">Blender context enabled</span>
          </PromptInputActionGroup>
          <PromptInputActionGroup>
            <PromptInputAction asChild>
              <Button
                type="button"
                size="icon-sm"
                disabled={!content.trim() || disabled}
                onClick={() => handleSubmit()}
                aria-label={disabled ? "Generating response" : "Send message"}
              >
                {disabled ? <LoaderCircle className="animate-spin" /> : <ArrowUp />}
              </Button>
            </PromptInputAction>
          </PromptInputActionGroup>
        </PromptInputActions>
      </PromptInput>
      <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground px-1">
        <span>Press <kbd className="px-1 py-0.5 rounded bg-muted border border-border text-muted-foreground">Enter</kbd> to generate, <kbd className="px-1 py-0.5 rounded bg-muted border border-border text-muted-foreground">Shift + Enter</kbd> for newline</span>
        <span>RAG Context Active</span>
      </div>
    </div>
  );
}
