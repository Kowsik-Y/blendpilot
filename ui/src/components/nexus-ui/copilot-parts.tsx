"use client";

import { useRef } from "react";
import {
  CheckCircle2,
  ChevronDown,
  FileImage,
  FileText,
  ImageIcon,
  LoaderCircle,
  Paperclip,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

export type CopilotAttachment = {
  id: string;
  name: string;
  type: string;
  url?: string;
};

export type CopilotCitation = {
  title: string;
  source: string;
  score: number;
};

export function Suggestions({ items, onSelect, disabled = false }: { items: string[]; onSelect: (value: string) => void; disabled?: boolean }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <Button key={item} type="button" size="xs" variant="outline" disabled={disabled} onClick={() => onSelect(item)} className="rounded-full">
          {item}
        </Button>
      ))}
    </div>
  );
}

export function AttachmentPicker({ attachments, onChange, disabled = false }: { attachments: CopilotAttachment[]; onChange: (attachments: CopilotAttachment[]) => void; disabled?: boolean }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const selectFiles = (files: FileList | null) => {
    if (!files) return;
    const next = Array.from(files).slice(0, 4).map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}`,
      name: file.name,
      type: file.type || "application/octet-stream",
      url: file.type.startsWith("image/") ? URL.createObjectURL(file) : undefined,
    }));
    onChange([...attachments, ...next].slice(0, 4));
  };

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-1">
      <input ref={inputRef} className="sr-only" type="file" accept="image/*,.blend,.fbx,.glb,.gltf,.obj,.txt,.md" multiple onChange={(event) => selectFiles(event.target.files)} />
      <Button type="button" variant="ghost" size="icon-sm" disabled={disabled} onClick={() => inputRef.current?.click()} aria-label="Attach files">
        <Paperclip />
      </Button>
      {attachments.map((attachment) => (
        <Badge key={attachment.id} variant="secondary" className="max-w-44 gap-1 pr-1">
          {attachment.type.startsWith("image/") ? <ImageIcon /> : <FileText />}
          <span className="truncate">{attachment.name}</span>
          <Button type="button" variant="ghost" size="icon-xs" onClick={() => onChange(attachments.filter((item) => item.id !== attachment.id))} aria-label={`Remove ${attachment.name}`}>
            ×
          </Button>
        </Badge>
      ))}
    </div>
  );
}

export function AttachmentList({ attachments }: { attachments?: CopilotAttachment[] }) {
  if (!attachments?.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {attachments.map((attachment) => attachment.url ? (
        <a key={attachment.id} href={attachment.url} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-lg border border-border">
          {/* Native image preview keeps client-only object URLs usable. */}
          <img src={attachment.url} alt={attachment.name} className="size-20 object-cover" />
        </a>
      ) : (
        <Badge key={attachment.id} variant="outline" className="gap-1"><FileText />{attachment.name}</Badge>
      ))}
    </div>
  );
}

export function Citations({ sources }: { sources?: CopilotCitation[] }) {
  if (!sources?.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5 border-t border-border pt-2">
      {sources.map((source) => (
        <a key={`${source.source}-${source.title}`} href={source.source} target="_blank" rel="noreferrer" className="max-w-full">
          <Badge variant="outline" className="max-w-full gap-1"><FileText /><span className="truncate">{source.title}</span><span>{Math.round(source.score * 100)}%</span></Badge>
        </a>
      ))}
    </div>
  );
}

export function WorkflowTrace({ title, detail, status }: { title: string; detail: string; status: "running" | "done" | "failed" }) {
  return (
    <Collapsible className="rounded-lg border border-border bg-muted/30 px-2 py-1.5">
      <CollapsibleTrigger className="flex w-full items-center gap-2 text-left text-xs">
        {status === "done" ? <CheckCircle2 className="text-primary" /> : <LoaderCircle className={status === "running" ? "animate-spin text-primary" : "text-destructive"} />}
        <span className="flex-1 font-medium">{title}</span><ChevronDown />
      </CollapsibleTrigger>
      <CollapsibleContent className="pt-1 text-xs text-muted-foreground">{detail}</CollapsibleContent>
    </Collapsible>
  );
}

export type ChainOfThoughtStep = {
  id: string;
  title: string;
  detail: string;
  status: "running" | "done" | "failed";
};

/** A single expandable, streaming-aware execution trace for observable agent work. */
export function ChainOfThought({ steps, complete = false }: { steps: ChainOfThoughtStep[]; complete?: boolean }) {
  const active = steps.find((step) => step.status === "running");
  const completed = steps.filter((step) => step.status === "done").length;

  return (
    <Collapsible defaultOpen={steps.length < 2} className="rounded-xl border border-border bg-muted/30">
      <CollapsibleTrigger className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-xs">
        {complete ? <CheckCircle2 className="text-primary" /> : <LoaderCircle className="animate-spin text-primary" />}
        <span className="flex-1 font-medium">{complete ? "Workflow complete" : active?.title || "Preparing workflow"}</span>
        <span className="text-muted-foreground">{completed}/{steps.length}</span>
        <ChevronDown />
      </CollapsibleTrigger>
      <CollapsibleContent className="border-t border-border px-3 py-2">
        <ol className="flex flex-col gap-2">
          {steps.map((step) => (
            <li key={step.id} className="flex items-start gap-2 text-xs">
              {step.status === "done" ? <CheckCircle2 className="mt-0.5 text-primary" /> : <LoaderCircle className={step.status === "running" ? "mt-0.5 animate-spin text-primary" : "mt-0.5 text-destructive"} />}
              <div className="min-w-0"><p className="font-medium">{step.title}</p><p className="text-muted-foreground">{step.detail}</p></div>
            </li>
          ))}
        </ol>
      </CollapsibleContent>
    </Collapsible>
  );
}

export function TextShimmer({ children }: { children: string }) {
  return <span className="animate-pulse text-muted-foreground">{children}</span>;
}

export function FeedbackBar({ onFeedback }: { onFeedback: (rating: "up" | "down") => void }) {
  return (
    <div className="flex items-center gap-1 text-muted-foreground">
      <span className="mr-1 text-[10px]">Helpful?</span>
      <Button type="button" size="icon-xs" variant="ghost" onClick={() => onFeedback("up")} aria-label="Helpful response"><ThumbsUp /></Button>
      <Button type="button" size="icon-xs" variant="ghost" onClick={() => onFeedback("down")} aria-label="Unhelpful response"><ThumbsDown /></Button>
    </div>
  );
}

export function ImageStatus({ count }: { count: number }) {
  if (!count) return null;
  return <span className="flex items-center gap-1 text-xs text-muted-foreground"><FileImage />{count} image{count === 1 ? "" : "s"} attached</span>;
}
