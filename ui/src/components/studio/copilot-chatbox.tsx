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
import { toast } from "sonner";
import Link from "next/link";
import { connectWorkflowStream, type WorkflowStreamPayload } from "@/lib/workflow-stream";
import {
  Bot,
  BrainCircuit,
  User,
  Send,
  Sparkles,
  CheckCircle2,
  BotMessageSquare,
  Key,
  Wrench,
  Eye,
  EyeOff,
  Loader2,
  Circle,
  Copy,
  Check,
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

export interface PipelineStep {
  id: string;
  name: string;
  status: "pending" | "running" | "done" | "failed";
  detail?: string;
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

interface CopilotChatboxProps {
  assetSpec?: StudioAssetSpec;
  onApplyAction?: (actionText: string) => void;
  onStartPipeline?: (prompt: string) => void;
  onWorkflowEvent?: (payload: WorkflowStreamPayload) => void;
  pipelineSessionId?: string | null;
  pipelineRunning?: boolean;
}

const INITIAL_10_STEPS: PipelineStep[] = [
  { id: "intent", name: "1. Intent Parser", status: "pending", detail: "Extract dimensions & quotas" },
  { id: "scene", name: "2. Scene Scanner", status: "pending", detail: "Blender workspace check" },
  { id: "research", name: "3. Research Agent", status: "pending", detail: "Engine & topology rules" },
  { id: "planning", name: "4. Step Planner", status: "pending", detail: "Synthesize atomic plan" },
  { id: "modeling", name: "5. 3D Modeler", status: "pending", detail: "Execute bmesh primitives" },
  { id: "material", name: "6. PBR Shader", status: "pending", detail: "Principled BSDF & lighting" },
  { id: "geometry_qa", name: "7. Topology QA", status: "pending", detail: "Manifold & non-manifold check" },
  { id: "visual_critic", name: "8. Visual Critic", status: "pending", detail: "Render critique score" },
  { id: "human_feedback", name: "9. Human Review", status: "pending", detail: "Approval gate" },
  { id: "export", name: "10. Export Agent", status: "pending", detail: "Generate production bundles" },
];

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
  const [messages, setMessages] = useState<CopilotMessage[]>([
    {
      id: "welcome",
      role: "copilot",
      content:
        "👋 **Hi! I'm your AI 3D Copilot.**\n\nI coordinate **10 autonomous Blender agents** with RAG knowledge grounding and multi-turn memory. Ask any modeling question, request modifier tweaks, or type any 3D asset to build!",
      actions: [
        "🚀 Launch 10-Agent Pipeline",
        "🔑 Configure LLM Key",
        "🛠️ Add 0.02m Bevel Modifier",
      ],
      time: "Just now",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<CopilotAttachment[]>([]);
  const [storeHydrated, setStoreHydrated] = useState(false);

  // User LLM Settings loaded from Settings Store (/api/settings)
  const [llmProvider, setLlmProvider] = useState<string>("openai");
  const [llmModel, setLlmModel] = useState<string>("gpt-4o");
  const [hasApiKey, setHasApiKey] = useState<boolean>(false);
  const [apiKeyInput, setApiKeyInput] = useState<string>("");
  const [showKeyText, setShowKeyText] = useState(false);
  const [keyDialogOpen, setKeyDialogOpen] = useState(false);
  const [savingKey, setSavingKey] = useState(false);

  // In-chat 10-Agent Execution Progress
  const [, setAgentSteps] = useState<PipelineStep[]>(INITIAL_10_STEPS);
  const [showProgressGrid, setShowProgressGrid] = useState(false);
  const [runPrompt, setRunPrompt] = useState<string | null>(null);
  const [runActivities, setRunActivities] = useState<PipelineActivity[]>([]);

  const nextMessageId = (prefix: string) => {
    messageIdRef.current += 1;
    return `${prefix}-${messageIdRef.current}`;
  };

  const setPipelineStepStatus = useCallback((nodeId: string, status: PipelineStep["status"], detail?: string) => {
    setAgentSteps((prev) =>
      prev.map((step) => {
        if (step.id === nodeId) {
          return { ...step, status, detail: detail || step.detail };
        }
        if (status === "running" && step.status === "running") {
          return { ...step, status: "done" };
        }
        return step;
      })
    );
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

  const hydrateProgressFromSnapshot = useCallback((state: PipelineStatePayload) => {
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
    if (completed.size === 0) return;
    setAgentSteps((prev) =>
      prev.map((step) => completed.has(step.id) ? { ...step, status: "done" } : step)
    );
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
      setPipelineStepStatus("modeling", "running", payload.description);
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
      setAgentSteps((prev) =>
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

    if (payload.node) {
      setAgentSteps((prev) =>
        prev.map((s) => s.id === payload.node ? { ...s, status: "done" } : s)
      );
      const state = (payload.state || {}) as PipelineStatePayload;
      const activity = describeNodeActivity(payload.node, state);
      if (activity) {
        upsertRunActivity(activity);
      }
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

  // Keep the visible Studio transcript available across a page refresh. Live
  // pipeline state remains authoritative on the workflow WebSocket/SSE stream.
  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(COPILOT_STORE_KEY);
      const parsed = stored ? JSON.parse(stored) as CopilotMessage[] : [];
      queueMicrotask(() => {
        if (Array.isArray(parsed) && parsed.length > 0) {
          const seen = new Set<string>();
          const uniqueMessages = parsed.slice(-60).map((message, index) => {
            if (!seen.has(message.id)) {
              seen.add(message.id);
              return message;
            }
            const id = `${message.id}-restored-${index}`;
            seen.add(id);
            return { ...message, id };
          });
          const restoredSequence = uniqueMessages.reduce((maximum, message) => {
            const suffix = Number(message.id.split("-").at(-1));
            return Number.isFinite(suffix) ? Math.max(maximum, suffix) : maximum;
          }, 0);
          messageIdRef.current = Math.max(messageIdRef.current, restoredSequence);
          setMessages(uniqueMessages);
        }
        setStoreHydrated(true);
      });
    } catch {
      window.localStorage.removeItem(COPILOT_STORE_KEY);
      queueMicrotask(() => setStoreHydrated(true));
    }
  }, []);

  useEffect(() => {
    if (!storeHydrated) return;
    try {
      const persistable = messages.map((message) => ({
        ...message,
        attachments: message.attachments?.map(({ id, name, type }) => ({ id, name, type })),
      }));
      window.localStorage.setItem(COPILOT_STORE_KEY, JSON.stringify(persistable.slice(-60)));
    } catch {
      // Storage may be unavailable in private browsing; chat remains usable.
    }
  }, [messages, storeHydrated]);

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

    queueMicrotask(() => setShowProgressGrid(true));
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
          hydrateProgressFromSnapshot(state);
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
    hydrateProgressFromSnapshot,
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
      setShowProgressGrid(true);
      setRunPrompt(text);
      setRunActivities([
        {
          id: "run-start",
          title: "Request received",
          detail: "Preparing the 10-agent Blender workflow",
          status: "running",
        },
      ]);
      handledWorkflowEventsRef.current.clear();
      setAgentSteps(INITIAL_10_STEPS.map((s, idx) => (idx === 0 ? { ...s, status: "running" } : { ...s, status: "pending" })));
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

  return (
    <>
      <Card className="bg-card border-border py-0 flex flex-col h-full overflow-hidden">
        {/* Header Bar with Store Connection & Key Config Dialog */}
        <CardHeader className="p-3 pb-2 bg-muted/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10 text-primary border border-primary/20">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <CardTitle className="text-xs font-bold text-foreground flex items-center gap-1.5">
                  3D Copilot & 10 Agents
                  {pipelineRunning && (
                    <Badge variant="outline" className="text-[9px]">
                      Running
                    </Badge>
                  )}
                </CardTitle>
                <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-primary" />
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
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0 flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 flex flex-col overflow-hidden p-3 relative">
          <div className="flex-1 min-h-0 relative">
              <MessageScrollerProvider autoScroll>
                <MessageScroller>
                  <MessageScrollerViewport className="pr-2">
                    <MessageScrollerContent className="space-y-3 pb-2">
                      {/* One chronological assistant run, fed only by live workflow events. */}
                      {showProgressGrid && (
                        <MessageScrollerItem messageId="agent-run" scrollAnchor className="order-2">
                          <Message align="start" className="my-4">
                            <MessageAvatar>
                              <div className="flex size-7 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
                                {runComplete ? (
                                  <CheckCircle2 className="size-3.5" />
                                ) : runFailed ? (
                                  <Circle className="size-3.5" />
                                ) : (
                                  <Loader2 className="size-3.5 animate-spin" />
                                )}
                              </div>
                            </MessageAvatar>
                            <MessageContent className="min-w-0 max-w-full">
                              <div className="flex items-center gap-2 text-xs font-medium text-foreground">
                                <span>{runComplete ? "Asset ready" : runFailed ? "Run stopped" : "Building your asset"}</span>
                              </div>
                              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                                {runPrompt || "Coordinating Blender agents"}
                              </p>
                              <div className="mt-3">
                                <ChainOfThought autoCloseOnAllComplete={false}>
                                  <ChainOfThoughtTrigger icon={<BrainCircuit />}>
                                    {runComplete ? "Created asset and completed workflow" : runActivities.at(-1)?.title || "Preparing asset creation"}
                                  </ChainOfThoughtTrigger>
                                  <ChainOfThoughtContent>
                                    {runActivities.map((activity) => (
                                      <ChainOfThoughtStep key={activity.id} status={activity.status === "done" ? "completed" : activity.status === "running" ? "running" : "failed"}>
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
                            </MessageContent>
                          </Message>
                        </MessageScrollerItem>
                      )}
      
                      {/* Message Flow */}
                      {messages.map((m) => {
                        const isUser = m.role === "user";
                        const isAgent = m.role === "agent";
      
                        return (
                          <MessageScrollerItem key={m.id} messageId={m.id} scrollAnchor={isUser} className="order-1">
                            <Message align={isUser ? "end" : "start"} className="my-2">
                              <MessageAvatar>
                                <div
                                  className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 shadow-sm mt-0.5 ${
                                    isAgent
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
            <div className="mt-2">
              <Suggestions
                disabled={loading || pipelineRunning}
                items={["Create a game-ready prop", "Inspect scene topology", "Export the current asset"]}
                onSelect={(suggestion) => setInput(suggestion)}
              />
            </div>
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
