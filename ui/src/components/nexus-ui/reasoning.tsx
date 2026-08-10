"use client";

import * as React from "react";
import { ChevronDown, Lightbulb, LoaderCircle } from "lucide-react";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

const ReasoningContext = React.createContext<{ isStreaming: boolean }>({ isStreaming: false });

function Reasoning({ children, isStreaming = false, className }: React.ComponentProps<"div"> & { isStreaming?: boolean }) {
  const [open, setOpen] = React.useState(true);

  return (
    <ReasoningContext.Provider value={{ isStreaming }}>
      <Collapsible open={open} onOpenChange={setOpen} className={cn("w-full group", className)}>
        {children}
      </Collapsible>
    </ReasoningContext.Provider>
  );
}

function ReasoningTrigger({ children, className }: React.ComponentProps<typeof CollapsibleTrigger>) {
  const { isStreaming } = React.useContext(ReasoningContext);
  
  return (
    <CollapsibleTrigger className={cn("flex w-fit items-center gap-2 text-left text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition-colors", className)}>
      {isStreaming ? <LoaderCircle className="w-3.5 h-3.5 animate-spin" /> : <Lightbulb className="w-3.5 h-3.5" />}
      <span className="flex-1">{children || "Agent is thinking..."}</span>
      <ChevronDown className="w-3.5 h-3.5 transition-transform duration-200 group-data-[state=open]:rotate-180" />
    </CollapsibleTrigger>
  );
}

function ReasoningContent({ children, className }: React.ComponentProps<typeof CollapsibleContent>) {
  return (
    <CollapsibleContent className={cn("pt-3 text-muted-foreground", className)}>
      <div className="border-l-2 border-border/50 pl-4 py-1 text-xs">
        {children}
      </div>
    </CollapsibleContent>
  );
}

export { Reasoning, ReasoningTrigger, ReasoningContent };
