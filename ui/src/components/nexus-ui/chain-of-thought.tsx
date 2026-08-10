"use client";

import * as React from "react";
import { CheckCircle2, ChevronDown, Circle, LoaderCircle } from "lucide-react";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

type ThoughtStatus = "pending" | "running" | "completed" | "failed";

const ThoughtContext = React.createContext<{ open: boolean; setOpen: (open: boolean) => void } | null>(null);

function ChainOfThought({ children, autoCloseOnAllComplete = true, className }: React.ComponentProps<"div"> & { autoCloseOnAllComplete?: boolean }) {
  const [open, setOpen] = React.useState(true);
  // Kept in the public API so callers can choose their preferred completion
  // behavior. Studio keeps the trace available after completion.
  void autoCloseOnAllComplete;

  return (
    <ThoughtContext.Provider value={{ open, setOpen }}>
      <Collapsible open={open} onOpenChange={setOpen} className={cn("w-full", className)}>{children}</Collapsible>
    </ThoughtContext.Provider>
  );
}

function ChainOfThoughtTrigger({ children, icon, className }: React.ComponentProps<typeof CollapsibleTrigger> & { icon?: React.ReactNode }) {
  return <CollapsibleTrigger className={cn("flex w-full items-center gap-2 py-1 text-left text-sm text-foreground", className)}>{icon ?? <LoaderCircle className="animate-spin text-primary" />}<span className="flex-1 font-medium">{children}</span><ChevronDown className="text-muted-foreground" /></CollapsibleTrigger>;
}

function ChainOfThoughtContent({ children, className }: React.ComponentProps<typeof CollapsibleContent>) {
  return <CollapsibleContent className={cn("pl-1 pt-3", className)}><ol className="flex flex-col gap-3">{children}</ol></CollapsibleContent>;
}

function ChainOfThoughtStep({ children, status = "pending", className }: React.ComponentProps<"li"> & { status?: ThoughtStatus }) {
  const icon = status === "completed" ? <CheckCircle2 className="mt-0.5 text-primary h-3 w-3" /> : status === "running" ? <LoaderCircle className="mt-0.5 animate-spin text-primary" /> : status === "failed" ? <Circle className="mt-0.5 text-destructive" /> : <Circle className="mt-0.5 text-muted-foreground" />;
  return <li data-status={status} className={cn("flex items-start gap-2 text-sm text-muted-foreground", className)}>{icon}<div className="min-w-0">{children}</div></li>;
}

function ChainOfThoughtStepTitle({ children, icon, className }: React.ComponentProps<"p"> & { icon?: React.ReactNode }) {
  return <p className={cn("flex items-center gap-1.5 font-normal", className)}>{icon}{children}</p>;
}

function ChainOfThoughtComplete({ label = "Task complete", icon, className }: { label?: string; icon?: React.ReactNode; className?: string }) {
  return <li className={cn("flex items-center gap-2 pt-1 text-sm font-medium text-foreground", className)}>{icon ?? <CheckCircle2 className="text-primary" />}{label}</li>;
}

export { ChainOfThought, ChainOfThoughtComplete, ChainOfThoughtContent, ChainOfThoughtStep, ChainOfThoughtStepTitle, ChainOfThoughtTrigger };
