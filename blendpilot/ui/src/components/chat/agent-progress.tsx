"use client";

import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";

export interface ProgressStep {
  id: string;
  name: string;
  status: "pending" | "running" | "done" | "failed";
  detail?: string;
}

export function AgentProgress({ steps }: { steps: ProgressStep[] }) {
  if (!steps || steps.length === 0) return null;

  return (
    <div className="my-3 p-3.5 rounded-xl bg-card border border-border text-xs shadow-sm">
      <div className="font-semibold text-foreground mb-2.5 flex items-center justify-between">
        <span>Agent Execution Pipeline</span>
        <span className="text-[10px] text-muted-foreground font-mono">
          {steps.filter((s) => s.status === "done").length}/{steps.length} completed
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {steps.map((step) => {
          return (
            <div
              key={step.id}
              className={`flex items-center gap-2 p-2 rounded-lg border transition-colors ${
                step.status === "done"
                  ? "bg-muted border-border text-foreground"
                  : step.status === "running"
                  ? "bg-accent border-border text-accent-foreground animate-pulse"
                  : step.status === "failed"
                  ? "bg-destructive/10 border-destructive/30 text-destructive"
                  : "bg-muted/40 border-border/60 text-muted-foreground"
              }`}
            >
              {step.status === "done" ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-primary shrink-0" />
              ) : step.status === "running" ? (
                <Loader2 className="w-3.5 h-3.5 text-primary animate-spin shrink-0" />
              ) : step.status === "failed" ? (
                <XCircle className="w-3.5 h-3.5 text-destructive shrink-0" />
              ) : (
                <Circle className="w-3.5 h-3.5 text-muted-foreground/60 shrink-0" />
              )}
              <div className="truncate">
                <p className="font-medium truncate">{step.name}</p>
                {step.detail && <p className="text-[10px] opacity-75 truncate">{step.detail}</p>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
