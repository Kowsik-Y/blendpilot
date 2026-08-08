"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";

import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type PromptInputContextValue = {
  onSubmit?: (value: string) => void;
};

const PromptInputContext = React.createContext<PromptInputContextValue | null>(null);

type PromptInputProps = Omit<React.ComponentProps<"div">, "onSubmit"> & {
  onSubmit?: (value: string) => void;
};

function PromptInput({ className, onSubmit, ...props }: PromptInputProps) {
  return (
    <PromptInputContext.Provider value={{ onSubmit }}>
      <div
        data-slot="prompt-input"
        role="group"
        aria-label="Chat input"
        className={cn(
          "flex w-full cursor-text flex-col overflow-hidden rounded-3xl border border-input bg-card shadow-sm transition-shadow focus-within:ring-3 focus-within:ring-ring/50",
          className,
        )}
        {...props}
      />
    </PromptInputContext.Provider>
  );
}

const PromptInputTextarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<typeof Textarea>
>(function PromptInputTextarea({ className, onKeyDown, ...props }, ref) {
  const context = React.useContext(PromptInputContext);

  return (
    <Textarea
      ref={ref}
      data-slot="prompt-input-textarea"
      rows={1}
      aria-label="Message input"
      className={cn(
        "min-h-14 max-h-44 resize-none border-0 bg-transparent px-4 py-3 text-sm leading-6 shadow-none focus-visible:ring-0",
        className,
      )}
      onKeyDown={(event) => {
        if (event.key === "Enter" && !event.shiftKey && context?.onSubmit) {
          event.preventDefault();
          context.onSubmit(event.currentTarget.value);
        }
        onKeyDown?.(event);
      }}
      {...props}
    />
  );
});

function PromptInputActions({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="prompt-input-actions"
      className={cn("flex items-center justify-between gap-2 px-3 pb-3", className)}
      {...props}
    />
  );
}

function PromptInputActionGroup({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="prompt-input-action-group" className={cn("flex items-center gap-1", className)} {...props} />;
}

function PromptInputAction({ asChild = false, ...props }: React.ComponentProps<"div"> & { asChild?: boolean }) {
  const Component = asChild ? Slot : "div";
  return <Component data-slot="prompt-input-action" {...props} />;
}

export {
  PromptInput,
  PromptInputTextarea,
  PromptInputActions,
  PromptInputActionGroup,
  PromptInputAction,
};
