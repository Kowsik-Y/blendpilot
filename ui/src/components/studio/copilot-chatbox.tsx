"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  MessageScroller,
  MessageScrollerProvider,
  MessageScrollerViewport,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerButton,
} from "@/components/ui/message-scroller";
import {
  Message,
  MessageAvatar,
  MessageContent,
  MessageFooter,
} from "@/components/ui/message";
import { Bubble, BubbleContent } from "@/components/ui/bubble";
import {
  PromptInput,
  PromptInputActionGroup,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/nexus-ui/prompt-input";
import {
  AttachmentList,
  AttachmentPicker,
  Citations,
  FeedbackBar,
  ImageStatus,
  Suggestions,
  TextShimmer,
  type CopilotAttachment,
  type CopilotCitation,
} from "@/components/nexus-ui/copilot-parts";
import {
  ChainOfThought,
  ChainOfThoughtComplete,
  ChainOfThoughtContent,
  ChainOfThoughtStep,
  ChainOfThoughtStepTitle,
  ChainOfThoughtTrigger,
} from "@/components/nexus-ui/chain-of-thought";
import { AGENT_DEFINITIONS } from "@/components/studio/agent-timeline";
import { toast } from "sonner";
import Link from "next/link";
import { connectWorkflowStream, type WorkflowStreamPayload } from "@/lib/workflow-stream";
import {
  Bot,
  BrainCircuit,
  User,
  Send,
  Sparkles,
  BotMessageSquare,
  Key,
  Wrench,
  Eye,
  EyeOff,
  Loader2,
  Copy,
  Check,
  Command,
  WandSparkles,
  Maximize2,
} from "lucide-react";

export interface CopilotMessage {
  id: string;
  role: "user" | "copilot" | "agent";
  agentName?: string;
  agentStep?: number;
  content: string;
  actions?: string[];
  status?: "pending" | "running" | "done" | "failed";
  time: string;
  isLiveLLM?: boolean;
  eventKey?: string;
  attachments?: CopilotAttachment[];
  citations?: CopilotCitation[];
}

interface PipelineActivity {
  id: string;
  title: string;
  detail: string;
  status: "running" | "done" | "failed";
  tool?: string;
}

interface StudioAssetSpec {
  asset_type?: string;
  dimensions?: {
    width?: number;
    depth?: number;
    height?: number;
  };
  triangle_limit?: number;
  budget?: {
    target_triangles?: number;
  };
}

interface PipelineStatePayload {
  current_agent?: string;
  design_spec?: StudioAssetSpec;
  geometry_score?: number;
  visual_score?: number;
  events?: Array<Record<string, unknown>>;
  stream_events?: WorkflowStreamPayload[];
}

interface StageStatus {
  id: string;
  title: string;
  detail: string;
  status: "pending" | "running" | "done" | "failed";
}

const AGENT_NODE_ALIASES: Record<string, string> = {
  intent_agent: "intent",
  scene_agent: "scene",
  research_agent: "research",
  planning_agent: "planning",
  modeling_agent: "modeling",
  material_agent: "material",
  geometry_qa_agent: "geometry_qa",
  geometry_repair: "geometry_qa",
  visual_critic_agent: "visual_critic",
  visual_repair: "visual_critic",
  feedback_agent: "human_feedback",
  export_agent: "export",
};

function toStageId(node?: string | null) {
  if (!node) return null;
  return AGENT_NODE_ALIASES[node] || node;
}

interface CopilotChatboxProps {
  assetSpec?: StudioAssetSpec;
  onApplyAction?: (actionText: string) => void;
  onStartPipeline?: (prompt: string) => void;
  onWorkflowEvent?: (payload: WorkflowStreamPayload) => void;
  pipelineSessionId?: string | null;
  pipelineRunning?: boolean;
}

function createStageStatuses(): StageStatus[] {
  return AGENT_DEFINITIONS.map((agent) => ({
    id: agent.id,
    title: agent.name,
    detail: agent.desc,
    status: "pending",
  }));
}

const COPILOT_STORE_KEY = "blendpilot:studio-copilot:v1";
export function CopilotChatbox({
  assetSpec,
  onApplyAction,
  onStartPipeline,
  onWorkflowEvent,
  pipelineSessionId,
  pipelineRunning = false,
}: CopilotChatboxProps) {
  const messageIdRef = useRef(0);
  const handledWorkflowEventsRef = useRef<Set<string>>(new Set());
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<CopilotAttachment[]>([]);

  // User LLM Settings loaded from Settings Store (/api/settings)
  const [llmProvider, setLlmProvider] = useState<string>("openai");
  const [llmModel, setLlmModel] = useState<string>("gpt-4o");
  const [hasApiKey, setHasApiKey] = useState<boolean>(false);
  const [apiKeyInput, setApiKeyInput] = useState<string>("");
  const [showKeyText, setShowKeyText] = useState(false);
  const [keyDialogOpen, setKeyDialogOpen] = useState(false);
  const [savingKey, setSavingKey] = useState(false);

  // In-chat LangGraph Execution Progress
  const [stageStatuses, setStageStatuses] = useState<StageStatus[]>(createStageStatuses());
  const [runPrompt, setRunPrompt] = useState<string | null>(null);
  const [runActivities, setRunActivities] = useState<PipelineActivity[]>([]);
  const [activeStage, setActiveStage] = useState<string | null>(null);

  const nextMessageId = (prefix: string) => {
    messageIdRef.current += 1;
    return `${prefix}-${messageIdRef.current}`;
  };

  const setPipelineStepStatus = useCallback((nodeId: string, status: StageStatus["status"], detail?: string) => {
    const stageId = toStageId(nodeId);
    if (!stageId) return;
    setStageStatuses((prev) =>
      prev.map((step) => {
        if (step.id === stageId) {
          return { ...step, status, detail: detail || step.detail };
        }
        if (status === "running" && step.status === "running") {
          return { ...step, status: "done" };
        }
        return step;
      })
    );
    setActiveStage(stageId);
  }, []);

  const markWorkflowEventHandled = useCallback((payload: WorkflowStreamPayload) => {
    const key =
      typeof payload.event_id === "number"
        ? `id:${payload.event_id}`
        : `${payload.event || "node"}:${payload.node || ""}:${payload.step_id || ""}:${payload.status || ""}`;
    if (handledWorkflowEventsRef.current.has(key)) {
      return false;
    }
    handledWorkflowEventsRef.current.add(key);
    return true;
  }, []);

  const upsertRunActivity = useCallback((activity: PipelineActivity) => {
    setRunActivities((prev) => {
      const existingIndex = prev.findIndex((item) => item.id === activity.id);
      if (existingIndex >= 0) {
        const next = [...prev];
        next[existingIndex] = { ...next[existingIndex], ...activity };
        return next;
      }
      return [...prev, activity].slice(-32);
    });
  }, []);

  const describeNodeActivity = useCallback((node: string, state: PipelineStatePayload): PipelineActivity | null => {
    if (node === "intent" && state.design_spec) {
      const spec = state.design_spec;
      return {
        id: "node:intent",
        title: "Intent understood",
        detail: `${spec.asset_type || "asset"} · ${spec.dimensions?.width || 1}m x ${spec.dimensions?.depth || 1}m x ${spec.dimensions?.height || 1}m · target < ${spec.budget?.target_triangles || 8000} tris`,
        status: "done",
      };
    }
    if (node === "scene") {
      return { id: "node:scene", title: "Scene scanned", detail: "Workspace checked and origin calibrated", status: "done" };
    }
    if (node === "research") {
      return { id: "node:research", title: "Constraints grounded", detail: "Engine profile, PBR rules, and topology constraints applied", status: "done" };
    }
    if (node === "planning") {
      return { id: "node:planning", title: "Plan synthesized", detail: "Executable Blender operations prepared", status: "done" };
    }
    if (node === "modeling") {
      return { id: "node:modeling", title: "Geometry built", detail: "Primitive operations completed and modifiers applied", status: "done" };
    }
    if (node === "material") {
      return { id: "node:material", title: "Materials assigned", detail: "PBR material and preview lighting configured", status: "done" };
    }
    if (node === "geometry_qa") {
      const score = state.geometry_score !== undefined ? Math.round(state.geometry_score * 100) : 100;
      return { id: "node:geometry_qa", title: "Topology checked", detail: `${score}% geometry pass rate`, status: "done" };
    }
    if (node === "visual_critic") {
      const score = state.visual_score !== undefined ? Math.round(state.visual_score * 100) : 88;
      return { id: "node:visual_critic", title: "Visual critique complete", detail: `${score}% visual quality score`, status: "done" };
    }
    if (node === "export") {
      return { id: "node:export", title: "Export packaged", detail: ".blend, .fbx, and .glb bundle ready", status: "done" };
    }
    return null;
  }, []);

  const hydrateGraphStagesFromSnapshot = useCallback((state: PipelineStatePayload) => {
    const completed = new Set<string>();
    const events = Array.isArray(state.events) ? state.events : [];
    for (const event of events) {
      if (!event || typeof event !== "object") continue;
      const agentName = "agent_name" in event ? String(event.agent_name) : "";
      const status = "status" in event ? String(event.status) : "";
      if (status !== "COMPLETED") continue;
      if (agentName === "intent_agent") completed.add("intent");
      if (agentName === "scene_agent") completed.add("scene");
      if (agentName === "research_agent") completed.add("research");
      if (agentName === "planning_agent") completed.add("planning");
      if (agentName === "modeling_agent") completed.add("modeling");
      if (agentName === "material_agent") completed.add("material");
      if (agentName === "geometry_qa_agent") completed.add("geometry_qa");
      if (agentName === "visual_critic_agent") completed.add("visual_critic");
      if (agentName === "feedback_agent") completed.add("human_feedback");
      if (agentName === "export_agent") completed.add("export");
    }
    setStageStatuses((prev) =>
      prev.map((step) => {
        if (completed.has(step.id)) {
          return { ...step, status: "done" };
        }
        if (step.id === toStageId(state.current_agent)) {
          return { ...step, status: "running" };
        }
        return step;
      })
    );
    const currentStage = toStageId(state.current_agent);
    if (currentStage) {
      setActiveStage(currentStage);
    }
  }, []);

  const handlePipelineEvent = useCallback((payload: WorkflowStreamPayload, fromSnapshot = false) => {
    if (!fromSnapshot && !markWorkflowEventHandled(payload)) {
      return;
    }

    if (payload.event === "agent_state" && payload.node) {
      const status =
        payload.status === "FAILED" ? "failed" :
          payload.status === "COMPLETED" ? "done" :
            "running";
      setPipelineStepStatus(payload.node, status, payload.description);
      upsertRunActivity({
        id: `agent:${payload.node}`,
        title:
          status === "running"
            ? `Working on ${payload.node.replaceAll("_", " ")}`
            : `Finished ${payload.node.replaceAll("_", " ")}`,
        detail: payload.description || "Working through the next stage",
        status,
      });
      return;
    }

    if (payload.event === "plan_ready") {
      setPipelineStepStatus("planning", "done");
      upsertRunActivity({
        id: "plan-ready",
        title: "Execution plan ready",
        detail: `${payload.step_count || 0} Blender operations queued`,
        status: "done",
      });
      return;
    }

    if (payload.event === "tool_start") {
      setPipelineStepStatus(payload.node || "modeling", "running", payload.description);
      upsertRunActivity({
        id: `tool:${payload.step_id}`,
        title: `Running step ${payload.step_id}/${payload.total_steps}`,
        detail: payload.description || "Executing Blender tool",
        status: "running",
        tool: payload.tool,
      });
      return;
    }

    if (payload.event === "tool_result") {
      const ok = payload.status === "COMPLETED";
      upsertRunActivity({
        id: `tool:${payload.step_id}`,
        title: ok ? `Step ${payload.step_id} complete` : `Step ${payload.step_id} failed`,
        detail: ok
          ? `Completed via ${payload.tool}`
          : payload.error || "Unknown Blender tool error",
        status: ok ? "done" : "failed",
        tool: payload.tool,
      });
      return;
    }

    if (payload.event === "tool_recovered") {
      upsertRunActivity({
        id: `tool:${payload.step_id}`,
        title: `Step ${payload.step_id} recovered`,
        detail: payload.reasoning || "Recovered and completed",
        status: "done",
      });
      return;
    }

    if (payload.event === "workflow_complete") {
      const completed = String(payload.status || "").toUpperCase() === "COMPLETED";
      setStageStatuses((prev) =>
        prev.map((step) =>
          completed
            ? { ...step, status: "done" }
            : step.status === "running"
              ? { ...step, status: "failed" }
              : step
        )
      );
      upsertRunActivity({
        id: "workflow-complete",
        title: completed ? "Run complete" : "Run stopped",
        detail: completed
          ? "All confirmed orchestration stages finished"
          : payload.error || "The workflow ended before every stage could complete",
        status: completed ? "done" : "failed",
      });
      return;
    }

    if (payload.event === "workflow_missing" || payload.status === "FAILED") {
      setStageStatuses((prev) =>
        prev.map((step) =>
          step.id === toStageId(payload.node) || step.status === "running"
            ? { ...step, status: "failed" }
            : step
        )
      );
      upsertRunActivity({
        id: "workflow-error",
        title: "Workflow connection failed",
        detail: payload.error || "The workflow could not continue. Re-run the request to start a new session.",
        status: "failed",
      });
      return;
    }

    if (payload.node) {
      const stageId = toStageId(payload.node) || payload.node;
      setStageStatuses((prev) =>
        prev.map((s) => s.id === stageId ? { ...s, status: "done" } : s)
      );
      const state = (payload.state || {}) as PipelineStatePayload;
      const activity = describeNodeActivity(stageId, state);
      if (activity) {
        upsertRunActivity(activity);
      }
      setActiveStage(toStageId(state.current_agent) || stageId);
    }
  }, [describeNodeActivity, markWorkflowEventHandled, setPipelineStepStatus, upsertRunActivity]);

  const replayPipelineEvents = useCallback((events: WorkflowStreamPayload[]) => {
    for (const event of events) {
      handlePipelineEvent(event, true);
    }
  }, [handlePipelineEvent]);

  // Auto-fetch user settings on mount
  const loadSettings = async () => {
    try {
      const res = await fetch("/api/settings");
      if (res.ok) {
        const data = await res.json();
        setLlmProvider(data.llmProvider || "openai");
        setLlmModel(data.llmModel || "gpt-4o");
        setHasApiKey(data.hasApiKey || false);
      }
    } catch {
      // Fallback
    }
  };

  useEffect(() => {
    void Promise.resolve().then(loadSettings);
  }, []);

  // Save API Key & Model Configuration directly from Studio
  const handleSaveKeySettings = async () => {
    setSavingKey(true);
    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          llmProvider,
          llmModel,
          llmApiKey: apiKeyInput.trim(),
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to save settings");
      }

      toast.success(`Connected to ${llmProvider.toUpperCase()} (${llmModel})!`);
      setHasApiKey(true);
      setKeyDialogOpen(false);
      setApiKeyInput("");
      loadSettings();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to save API settings";
      toast.error(message);
    } finally {
      setSavingKey(false);
    }
  };

  // Listen to live pipeline WebSocket stream and update in-chat Agent Progress & Thought Bubbles
  useEffect(() => {
    if (!pipelineSessionId) return;

    handledWorkflowEventsRef.current.clear();
    const stream = connectWorkflowStream({
      sessionId: pipelineSessionId,
      onFallback: () => {
        toast.warning("Workflow WebSocket dropped. Reconnected through SSE.");
      },
      onMessage: (payload: WorkflowStreamPayload) => {
        try {
          onWorkflowEvent?.(payload);
          const state = (payload.state || {}) as PipelineStatePayload;

          if (payload.event === "snapshot") {
            hydrateGraphStagesFromSnapshot(state);
            if (Array.isArray(state.stream_events)) {
              replayPipelineEvents(state.stream_events);
            }
            return;
          }

          handlePipelineEvent(payload);
        } catch (e) {
          console.error("Workflow stream parse error", e);
        }
      },
    });

    return () => {
      stream.close();
    };
  }, [
    pipelineSessionId,
    onWorkflowEvent,
    handlePipelineEvent,
    hydrateGraphStagesFromSnapshot,
    replayPipelineEvents,
  ]);




  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || input).trim();
    if (!text || loading) return;

    if (text.includes("Configure LLM Key")) {
      setKeyDialogOpen(true);
      return;
    }

    const lower = text.toLowerCase();
    // Broad intent detection — let the LLM handle nuanced classification
    // Pipeline triggers: explicit launch commands OR any 3D creation verbs
    const creationVerbs = ["create", "make", "generate", "build", "design", "model", "construct", "sculpt", "craft"];
    const isCreationIntent =
      lower.includes("launch 10-agent") ||
      lower.includes("launch pipeline") ||
      lower.includes("run pipeline") ||
      creationVerbs.some((v) => lower.startsWith(v)) ||
      (creationVerbs.some((v) => lower.includes(v)) && lower.split(" ").length >= 3);

    // Creation intents flow to the autonomous workflow. Conversational and
    // inspection requests remain in chat; no manual plan mode is required.
    const shouldRunAgent = isCreationIntent && Boolean(onStartPipeline);

    if (shouldRunAgent && onStartPipeline) {
      const userMsg: CopilotMessage = {
        id: nextMessageId("user"),
        role: "user",
        content: text,
        attachments,
        time: "Just now",
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setAttachments([]);
      setRunPrompt(text);
      setRunActivities([
        {
          id: "run-start",
          title: "Request received",
          detail: "Preparing the 10-agent Blender workflow",
          status: "running",
        },
      ]);
      setStageStatuses(createStageStatuses().map((step, idx) => (idx === 0 ? { ...step, status: "running" } : step)));
      setActiveStage("intent");
      handledWorkflowEventsRef.current.clear();
      onStartPipeline(text);
      return; // 🛑 CRITICAL: Stop here so we don't ALSO trigger a standard chat LLM response
    }

    const userMsg: CopilotMessage = {
      id: nextMessageId("user"),
      role: "user",
      content: text,
      attachments,
      time: "Just now",
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setAttachments([]);
    setLoading(true);

    try {
      // Build multi-turn conversation memory for context window
      const history = messages
        .filter((m) => m.role === "user" || m.role === "copilot")
        .slice(-8)
        .map((m) => ({
          role: m.role === "user" ? "user" : "assistant",
          content: m.content,
        }));

      const res = await fetch("/api/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          asset_spec: assetSpec,
          conversation_history: history,
          attachments: attachments.map(({ name, type }) => ({ name, type })),
        }),
      });

      if (!res.ok) throw new Error("Copilot response error");
      const data = await res.json();

      const copilotMsg: CopilotMessage = {
        id: nextMessageId("copilot"),
        role: "copilot",
        content: data.reply,
        actions: data.suggested_actions || [],
        isLiveLLM: data.is_live_llm,
        citations: data.ragSources || [],
        time: "Just now",
      };
      setMessages((prev) => [...prev, copilotMsg]);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Copilot response error";
      setMessages((prev) => [
        ...prev,
        {
          id: nextMessageId("error"),
          role: "copilot",
          content: `⚠️ Copilot notice: ${message}`,
          time: "Just now",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const runFinished = runActivities.some((activity) => activity.id === "workflow-complete");
  const runFailed = runActivities.some(
    (activity) => activity.id === "workflow-complete" && activity.status === "failed"
  );
  const runComplete = runFinished && !runFailed;
  const liveStages = stageStatuses;

  return (
    <>
      <Card className="bg-card border-border py-0 flex flex-col h-full overflow-hidden">
        {/* Header Bar with Store Connection & Key Config Dialog */}
        <CardHeader className="p-3 pb-2 bg-muted/50">
          <CardTitle className="text-xs font-bold text-foreground flex items-center gap-1.5">
            <div className="text-[10px] text-muted-foreground flex items-center gap-1">
              <span className="font-medium text-foreground">{llmProvider.toUpperCase()}</span>
              <span>({llmModel})</span>
              {hasApiKey ? (
                <span className="flex items-center gap-0.5 text-emerald-400 font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Connected
                </span>
              ) : (
                <span className="flex items-center gap-0.5 text-orange-400 font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-orange-400" />
                  No Key
                </span>
              )}
            </div>
            {pipelineRunning && (
              <Badge variant="outline" className="text-[9px]">
                Running
              </Badge>
            )}
          </CardTitle>
        </CardHeader>

        <CardContent className="p-0 flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 flex flex-col overflow-hidden p-3 relative">
            <div className="flex-1 min-h-0 relative">
              <MessageScrollerProvider autoScroll>
                <MessageScroller>
                  <MessageScrollerViewport className="pr-2">
                    <MessageScrollerContent className="space-y-3 pb-2">
                      <MessageScrollerItem messageId="graph-console" scrollAnchor={false} className="order-0">
                        <div className="rounded-2xl border border-border/60 bg-background/70 p-3 shadow-sm">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                                <Command className="size-3.5" />
                                LangGraph Console
                              </div>
                              <div className="mt-1 text-sm font-medium text-foreground">
                                {runComplete ? "Asset ready" : runFailed ? "Run stopped" : runPrompt || "Awaiting workflow input"}
                              </div>
                              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                                {runComplete
                                  ? "The graph finished its production path and exported the asset."
                                  : runFailed
                                    ? "A node failed or the graph terminated early. Inspect the activity trail below."
                                    : "Live LangGraph nodes, tool calls, and repair loops stream here as execution advances."}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="text-[10px] uppercase tracking-[0.18em]">
                                {activeStage || "idle"}
                              </Badge>
                              <Badge variant="secondary" className="text-[10px] uppercase tracking-[0.18em]">
                                {runActivities.length} events
                              </Badge>
                            </div>
                          </div>

                          <div className="mt-3 rounded-xl border border-border/60 bg-background/60 p-3">
                            <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                              <span>Trace</span>
                              <span>Node by node</span>
                            </div>
                            <div className="space-y-1.5">
                              {liveStages.map((stage, index) => (
                                <div
                                  key={stage.id}
                                  className={`flex items-start gap-3 rounded-xl border px-3 py-2 transition-colors ${stage.status === "running"
                                    ? "border-cyan-500/40 bg-cyan-500/10"
                                    : stage.status === "done"
                                      ? "border-emerald-500/20 bg-emerald-500/5"
                                      : stage.status === "failed"
                                        ? "border-red-500/30 bg-red-500/5"
                                        : "border-transparent bg-muted/10"
                                    }`}
                                >
                                  <div className="mt-0.5 flex shrink-0 flex-col items-center">
                                    <span
                                      className={`size-2 rounded-full ${stage.status === "running"
                                        ? "bg-cyan-400"
                                        : stage.status === "done"
                                          ? "bg-emerald-400"
                                          : stage.status === "failed"
                                            ? "bg-red-400"
                                            : "bg-muted-foreground/50"
                                        }`}
                                    />
                                    {index < liveStages.length - 1 && (
                                      <span className="mt-1 h-5 w-px bg-border/70" />
                                    )}
                                  </div>

                                  <div className="min-w-0 flex-1">
                                    <div className="flex flex-wrap items-center gap-2">
                                      <span className="text-sm font-medium text-foreground">{stage.title}</span>
                                      <Badge variant="outline" className="text-[9px] uppercase tracking-[0.16em]">
                                        {stage.status}
                                      </Badge>
                                    </div>
                                    <div className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
                                      {stage.detail}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="mt-3">
                            <ChainOfThought autoCloseOnAllComplete={false}>
                              <ChainOfThoughtTrigger icon={<BrainCircuit />}>
                                {runComplete ? "Workflow finished" : runFailed ? "Workflow halted" : "Live graph trace"}
                              </ChainOfThoughtTrigger>
                              <ChainOfThoughtContent>
                                {runActivities.map((activity) => (
                                  <ChainOfThoughtStep
                                    key={activity.id}
                                    status={activity.status === "done" ? "completed" : activity.status === "running" ? "running" : "failed"}
                                  >
                                    <ChainOfThoughtStepTitle icon={activity.tool ? <Wrench /> : undefined}>
                                      {activity.tool ? `${activity.title} · ${activity.tool}` : activity.title}
                                    </ChainOfThoughtStepTitle>
                                    <p className="text-muted-foreground">{activity.detail}</p>
                                  </ChainOfThoughtStep>
                                ))}
                                {runComplete && <ChainOfThoughtComplete label="Asset workflow complete" />}
                              </ChainOfThoughtContent>
                            </ChainOfThought>
                          </div>
                        </div>
                      </MessageScrollerItem>

                      {/* Message Flow */}
                      {messages.map((m) => {
                        const isUser = m.role === "user";
                        const isAgent = m.role === "agent";

                        return (
                          <MessageScrollerItem key={m.id} messageId={m.id} scrollAnchor={isUser} className="order-1">
                            <Message align={isUser ? "end" : "start"} className="my-2">
                              <MessageAvatar>
                                <div
                                  className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 shadow-sm mt-0.5 ${isAgent
                                    ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30"
                                    : "bg-primary text-primary-foreground"
                                    }`}
                                >
                                  {isUser ? <User className="w-3.5 h-3.5" /> : isAgent ? <Sparkles className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                                </div>
                              </MessageAvatar>

                              <MessageContent>
                                <Bubble variant={isUser ? "default" : "outline"} align={isUser ? "end" : "start"} className="group relative transition-all duration-300">
                                  <BubbleContent>
                                    {/* Copy Action Button */}
                                    <button
                                      onClick={() => handleCopy(m.id, m.content)}
                                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-md bg-background/80 hover:bg-muted text-muted-foreground"
                                      title="Copy message"
                                    >
                                      {copiedId === m.id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                    </button>

                                    <AttachmentList attachments={m.attachments} />

                                    {/* Markdown Body */}
                                    <div className="prose prose-invert prose-xs max-w-none wrap-break-word">
                                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                                    </div>

                                    <Citations sources={m.citations} />

                                    {m.role !== "user" && (
                                      <div className="mt-3 grid gap-2 rounded-xl border border-border/60 bg-background/70 p-2 sm:grid-cols-2">
                                        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                                          <WandSparkles className="size-3.5 text-cyan-400" />
                                          Graph-aware reply
                                        </div>
                                        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                                          <Maximize2 className="size-3.5 text-primary" />
                                          Production operator console
                                        </div>
                                      </div>
                                    )}

                                    {/* Suggested actions are executable Studio prompts. */}
                                    {m.actions && m.actions.length > 0 && (
                                      <div className="mt-2.5 border-t border-border/40 pt-2">
                                        <Suggestions items={m.actions} disabled={loading || pipelineRunning} onSelect={(action) => {
                                          handleSend(action);
                                          onApplyAction?.(action);
                                        }} />
                                      </div>
                                    )}
                                  </BubbleContent>
                                </Bubble>

                                <MessageFooter className="mt-1 flex items-center justify-between text-[9px] text-muted-foreground/60 w-full">
                                  <span>{m.time}</span>
                                  {!isUser && <FeedbackBar onFeedback={(rating) => toast.success(rating === "up" ? "Feedback saved — thank you." : "Thanks — we’ll use that to improve the next response.")} />}
                                  {m.isLiveLLM && (
                                    <span className="text-cyan-400 font-mono flex items-center gap-0.5 ml-auto">
                                      <Sparkles className="w-2.5 h-2.5" /> Live LLM
                                    </span>
                                  )}
                                </MessageFooter>
                              </MessageContent>
                            </Message>
                          </MessageScrollerItem>
                        );
                      })}

                      {loading && (
                        <div className="order-2 flex items-center gap-2 p-2 text-xs text-muted-foreground">
                          <Loader2 className="w-4 h-4 animate-spin text-primary" />
                          <TextShimmer>{hasApiKey ? "Generating with " + llmProvider.toUpperCase() + "..." : "Processing..."}</TextShimmer>
                        </div>
                      )}
                    </MessageScrollerContent>
                  </MessageScrollerViewport>
                  <MessageScrollerButton />
                </MessageScroller>
              </MessageScrollerProvider>
            </div>
          </div>
          {/* Chat Input Bar with Plan Toggle */}
          <div className="border-t border-border p-3">
            <PromptInput onSubmit={handleSend}>
              <PromptInputTextarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Ask Copilot (e.g. ‘Make a sword’)"
                disabled={loading || pipelineRunning}
                className="min-h-12 px-3 py-2 text-xs"
              />
              <PromptInputActions>
                <PromptInputActionGroup>
                  <AttachmentPicker attachments={attachments} onChange={setAttachments} disabled={loading || pipelineRunning} />
                  <ImageStatus count={attachments.filter((attachment) => attachment.type.startsWith("image/")).length} />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setKeyDialogOpen(true)}
                    title="Configure the model that automatically selects the workflow tools"
                  >
                    <BotMessageSquare data-icon="inline-start" />
                    Auto
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setInput("Generate a LangGraph-driven Blender asset with live tool feedback, repair loops, and export readiness.");
                    }}
                  >
                    <Command data-icon="inline-start" />
                    Graph prompt
                  </Button>
                </PromptInputActionGroup>
                <PromptInputActionGroup>
                  <Button
                    type="button"
                    size="icon-sm"
                    onClick={() => handleSend()}
                    disabled={!input.trim() || loading || pipelineRunning}
                    aria-label="Send message"
                  >
                    {loading ? <Loader2 className="animate-spin" /> : <Send />}
                  </Button>
                </PromptInputActionGroup>
              </PromptInputActions>
            </PromptInput>
          </div>
        </CardContent>
      </Card>

      {/* Inline Quick LLM Key Configuration Dialog */}
      <Dialog open={keyDialogOpen} onOpenChange={setKeyDialogOpen}>
        <DialogContent className="max-w-md bg-card border-border shadow-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-foreground">
              <Key className="w-4 h-4 text-primary" />
              Configure LLM Provider & Key
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Link your API Key to enable real-time Claude, GPT-4o, or Gemini streaming and agent execution.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={(e) => { e.preventDefault(); handleSaveKeySettings(); }}>
            <div className="space-y-4 py-2">
              <div className="space-y-1.5">
                <Label className="text-xs text-foreground font-medium">Provider</Label>
                <Select value={llmProvider} onValueChange={(val) => {
                  if (!val) return;
                  setLlmProvider(val);
                  if (val === "anthropic") setLlmModel("claude-3-5-sonnet-20241022");
                  else if (val === "openai") setLlmModel("gpt-4o");
                  else if (val === "custom") setLlmModel("gemini-1.5-pro");
                }}>
                  <SelectTrigger className="h-9 text-xs bg-background">
                    <SelectValue placeholder="Select LLM Provider" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="openai">OpenAI (GPT-4o, GPT-4o-mini)</SelectItem>
                    <SelectItem value="anthropic">Anthropic (Claude 3.5 Sonnet)</SelectItem>
                    <SelectItem value="custom">Google Gemini / Custom Endpoint</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs text-foreground font-medium">Model Name</Label>
                <Input
                  value={llmModel}
                  onChange={(e) => setLlmModel(e.target.value)}
                  placeholder="gpt-4o or claude-3-5-sonnet-20241022"
                  className="h-9 text-xs bg-background"
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs text-foreground font-medium">
                  API Key {hasApiKey && <span className="text-emerald-400 font-mono">(Key Already Configured)</span>}
                </Label>
                <div className="relative">
                  <Input
                    type={showKeyText ? "text" : "password"}
                    value={apiKeyInput}
                    onChange={(e) => setApiKeyInput(e.target.value)}
                    placeholder={hasApiKey ? "••••••••••••••••••••••••" : "Paste sk-... or api key here"}
                    className="h-9 text-xs bg-background pr-9"
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowKeyText(!showKeyText)}
                    className="absolute right-2.5 top-2.5 text-muted-foreground hover:text-foreground"
                  >
                    {showKeyText ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-[10px] text-muted-foreground">
                  Keys are AES-256 encrypted server-side in your local database.
                </p>
              </div>
            </div>

            <DialogFooter className="flex items-center justify-between sm:justify-between">
              <Link href="/settings" className="text-xs text-cyan-400 hover:underline">
                Advanced Settings →
              </Link>
              <div className="flex gap-2">
                <Button type="button" size="sm" variant="ghost" onClick={() => setKeyDialogOpen(false)} className="text-xs">
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={savingKey || (!apiKeyInput.trim() && !hasApiKey)}
                  className="text-xs bg-primary text-primary-foreground gap-1.5"
                >
                  {savingKey ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                  Save & Connect
                </Button>
              </div>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
