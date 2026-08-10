"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

function TextShimmer({
  children,
  className,
  spread = 8,
  duration = 1.8,
  invertLight = false,
  disableShimmer = false,
}: React.ComponentProps<"span"> & {
  spread?: number;
  duration?: number;
  invertLight?: boolean;
  disableShimmer?: boolean;
}) {
  return (
    <span
      data-slot="text-shimmer"
      data-shimmer-disabled={disableShimmer || undefined}
      className={cn(
        "inline-block bg-[linear-gradient(110deg,var(--muted-foreground)_35%,var(--foreground)_50%,var(--muted-foreground)_65%)] bg-[length:200%_100%] bg-clip-text text-transparent",
        disableShimmer && "bg-none text-muted-foreground",
        invertLight && "dark:bg-[linear-gradient(110deg,var(--muted-foreground)_35%,var(--foreground)_50%,var(--muted-foreground)_65%)]",
        className,
      )}
      style={disableShimmer ? undefined : { animation: `nexus-text-shimmer ${duration}s linear infinite`, backgroundSize: `${spread * 25}% 100%` }}
    >
      {children}
    </span>
  );
}

export { TextShimmer };
