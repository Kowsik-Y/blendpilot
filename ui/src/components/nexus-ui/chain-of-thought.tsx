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
  return (
    <CollapsibleContent className={cn("pt-3", className)}>
      <ul className="relative flex flex-col gap-4 pl-8 before:absolute before:inset-y-2 before:left-3.75 before:w-px before:bg-border/40">
        {children}
      </ul>
    </CollapsibleContent>
  );
}

function ChainOfThoughtStep({ children, status = "pending", className }: React.ComponentProps<"li"> & { status?: ThoughtStatus }) {
  return (
    <li data-status={status} className={cn("relative flex flex-col gap-1 text-sm text-muted-foreground", className)}>
      {children}
    </li>
  );
}

function ChainOfThoughtStepTitle({ children, icon, className }: React.ComponentProps<"p"> & { icon?: React.ReactNode }) {
  return (
    <div className={cn("flex items-center gap-3 font-medium text-foreground", className)}>
      {icon && (
        <div className="absolute -left-6.25 flex h-5 w-5 items-center justify-center bg-card text-muted-foreground ring-4 ring-card">
          {icon}
        </div>
      )}
      {children}
    </div>
  );
}

function ChainOfThoughtComplete({ label = "Task complete", icon, className }: { label?: string; icon?: React.ReactNode; className?: string }) {
  return (
    <li className={cn("relative flex items-center gap-3 text-sm font-medium text-foreground", className)}>
      <div className="absolute -left-6.25 flex h-5 w-5 items-center justify-center bg-card text-primary ring-4 ring-card">
        {icon ?? <CheckCircle2 className="h-4 w-4" />}
      </div>
      {label}
    </li>
  );
}

export { ChainOfThought, ChainOfThoughtComplete, ChainOfThoughtContent, ChainOfThoughtStep, ChainOfThoughtStepTitle, ChainOfThoughtTrigger };
