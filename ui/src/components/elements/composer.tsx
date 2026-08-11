import type { ComponentProps } from "react";
import { CheckIcon, ChevronDownIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ComposerModel {
  name: string;
  meta: string;
}

export function ComposerMenu({
  open,
  align = "start",
  className,
  ...props
}: ComponentProps<"div"> & { open: boolean; align?: "start" | "end" }) {
  return (
    <div
      data-slot="composer-menu"
      data-open={open || undefined}
      className={cn(
        "bg-popover text-popover-foreground border shadow-md",
        "absolute bottom-full z-10 mb-2 flex w-72 flex-col gap-0.5 rounded-2xl p-1.5 max-h-[50vh] overflow-y-auto",
        align === "start"
          ? "inset-s-0 origin-bottom-left"
          : "inset-e-0 origin-bottom-right",
        "transition-[opacity,scale] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none",
        open
          ? "scale-100 opacity-100"
          : "pointer-events-none scale-[0.97] opacity-0",
        className,
      )}
      {...props}
    />
  );
}

export function ComposerMenuItem({
  active = false,
  className,
  ...props
}: ComponentProps<"button"> & { active?: boolean }) {
  return (
    <button
      type="button"
      data-slot="composer-menu-item"
      data-active={active || undefined}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-[10px] px-2.5 py-2 text-[13.5px] transition-colors",
        active ? "bg-accent text-accent-foreground" : "hover:bg-foreground/4",
        className,
      )}
      {...props}
    />
  );
}

export function ComposerModelTrigger({
  model,
  open,
  className,
  ...props
}: Omit<ComponentProps<"button">, "children"> & {
  model: string;
  open: boolean;
}) {
  return (
    <button
      type="button"
      aria-expanded={open}
      data-slot="composer-model-trigger"
      className={cn(
        "text-foreground/55 hover:bg-foreground/6 hover:text-foreground/90 dark:hover:bg-foreground/9 flex h-8 items-center gap-1.5 rounded-full px-3 text-[12.5px] transition-colors",
        className,
      )}
      {...props}
    >
      {model}
      <ChevronDownIcon className="size-3 opacity-60" />
    </button>
  );
}

export function ComposerModelItem({
  entry,
  selected,
  ...props
}: Omit<ComponentProps<"button">, "children"> & {
  entry: ComposerModel;
  selected: boolean;
}) {
  return (
    <ComposerMenuItem active={selected} {...props}>
      <span className="flex-1 text-start">{entry.name}</span>
      <span className={cn("font-mono", "text-foreground/35 tabular-nums")}>
        {entry.meta}
      </span>
      <span className="flex w-4 justify-end">
        {selected && (
          <CheckIcon className="fade-in zoom-in-90 animate-in size-3.5 duration-200" />
        )}
      </span>
    </ComposerMenuItem>
  );
}
