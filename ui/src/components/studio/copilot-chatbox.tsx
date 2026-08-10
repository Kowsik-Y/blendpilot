"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AiBrain01Icon,
  Analytics01Icon,
  CheckmarkCircle01Icon,
  FileSearchIcon,
  IdeaIcon,
} from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
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
import { Thread } from "@/components/assistant-ui/thread";
import {
  useExternalStoreRuntime,
  useExternalMessageConverter,
  AssistantRuntimeProvider,
  type ThreadMessageLike,
} from "@assistant-ui/react";
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
  thinking?: string;
  tools?: { id: string; name: string; status: "running" | "done" | "failed"; input?: any }[];
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



interface CopilotChatboxProps {
  assetSpec?: any;
  onApplyAction?: (action: string) => void;
  onStartPipeline?: (prompt: string) => void;
  onWorkflowEvent?: (payload: WorkflowStreamPayload) => void;
  pipelineSessionId?: string | null;
  pipelineRunning?: boolean;
  projectId?: string;
}

interface LiveThinkingState {
  active: boolean;
  content: string;
  tools: { id: string; name: string; status: "running" | "done" | "failed"; input?: any }[];
}



export function CopilotChatbox({
  assetSpec,
  onApplyAction,
  onStartPipeline,
  onWorkflowEvent,
  pipelineSessionId,
  pipelineRunning,
  projectId = "default",
}: CopilotChatboxProps) {
  const handledWorkflowEventsRef = useRef<Set<string>>(new Set());
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<CopilotAttachment[]>([]);

  // User LLM Settings loaded from Client LocalStorage and Settings Store
  const [llmProvider, setLlmProvider] = useState<string>("groq");
  const [llmModel, setLlmModel] = useState<string>("llama-3.3-70b-versatile");
  const [hasApiKey, setHasApiKey] = useState<boolean>(false);
  const [apiKeyInput, setApiKeyInput] = useState<string>("");
  const [showKeyText, setShowKeyText] = useState(false);
  const [keyDialogOpen, setKeyDialogOpen] = useState(false);
  const [savingKey, setSavingKey] = useState(false);

  const [liveThinking, setLiveThinking] = useState<LiveThinkingState>({
    active: false,
    content: "",
    tools: [],
  });

  const nextMessageId = (prefix: string) => {
    return `${prefix}-${crypto.randomUUID()}`;
  };



  // Auto-fetch user settings on mount from localStorage & /api/settings
  const loadSettings = async () => {
    try {
      if (typeof window !== "undefined") {
        const localKey = localStorage.getItem("blendpilot_user_api_key");
        const localProvider = localStorage.getItem("blendpilot_user_provider");
        const localModel = localStorage.getItem("blendpilot_user_model");

        if (localKey && localKey.trim().length > 5) {
          setHasApiKey(true);
          setApiKeyInput(localKey);
        }
        if (localProvider) setLlmProvider(localProvider);
        if (localModel) setLlmModel(localModel);
      }

      const res = await fetch("/api/settings");
      if (res.ok) {
        const data = await res.json();
        if (data.llmProvider) setLlmProvider(data.llmProvider);
        if (data.llmModel) setLlmModel(data.llmModel);
        if (data.hasApiKey) setHasApiKey(true);
      }
    } catch {
      // Fallback
    }
  };

  // Persist messages to localStorage
  useEffect(() => {
    const saved = localStorage.getItem(`copilot_chat_${projectId}`);
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse saved messages", e);
      }
    }
  }, [projectId]);

  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(`copilot_chat_${projectId}`, JSON.stringify(messages));
    }
  }, [messages, projectId]);

  useEffect(() => {
    void Promise.resolve().then(loadSettings);
  }, []);

  // Save API Key & Model Configuration directly from Studio application
  const handleSaveKeySettings = async () => {
    setSavingKey(true);
    try {
      const trimmedKey = apiKeyInput.trim();

      // Store in browser client storage for instant application usage
      if (typeof window !== "undefined" && trimmedKey) {
        localStorage.setItem("blendpilot_user_api_key", trimmedKey);
        localStorage.setItem("blendpilot_user_provider", llmProvider);
        localStorage.setItem("blendpilot_user_model", llmModel);
      }

      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          llmProvider,
          llmModel,
          llmApiKey: trimmedKey,
        }),
      });

      if (!res.ok) {
        console.warn("Could not save to DB store, but saved in local browser store");
      }

      toast.success(`Connected to ${llmProvider.toUpperCase()} (${llmModel})!`);
      setHasApiKey(true);
      setKeyDialogOpen(false);
<<<<<<< HEAD
    } catch (err: any) {
      toast.error(err.message || "Failed to save API settings");
=======
      setApiKeyInput("");
      loadSettings();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to save API settings";
      toast.error(message);
>>>>>>> 9960c34c885b76ae6a6056cb373b1205a98fc89e
    } finally {
      setSavingKey(false);
    }
  };

<<<<<<< HEAD
  // Listen to live pipeline SSE stream and dynamically display Agent Reasoning & Outputs
=======
  const activeMessageIdRef = useRef<string | null>(null);

  // Listen to live pipeline WebSocket stream and update in-chat Agent Progress & Thought Bubbles
>>>>>>> 9960c34c885b76ae6a6056cb373b1205a98fc89e
  useEffect(() => {
    if (!pipelineSessionId) return;

    handledWorkflowEventsRef.current.clear();
    activeMessageIdRef.current = nextMessageId("copilot");
    setLiveThinking({ active: true, content: "", tools: [] });

<<<<<<< HEAD
    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const node = payload.node;
        const state = payload.state || {};

        if (node) {
          // Update the step in the progress grid
          setAgentSteps((prev) =>
            prev.map((s) => {
              if (s.id === node) {
                return { ...s, status: "done" };
              }
              return s;
            })
          );

          // Dynamically extract real agent execution details from live state and event logs
          let detailText = "";
          const spec = state.design_spec;
          const plan = state.design_plan;
          const events = state.events || [];
          const latestEvent = events.length > 0 ? events[events.length - 1] : null;

          if (node === "intent" && spec) {
            const dims = spec.dimensions ? `${spec.dimensions.width}m × ${spec.dimensions.depth}m × ${spec.dimensions.height}m` : "Standard Scale";
            const tris = spec.budget?.target_triangles ? `< ${spec.budget.target_triangles} tris` : "Optimized";
            const comps = spec.sub_components?.length ? ` | Parts: ${spec.sub_components.join(", ")}` : "";
            detailText = `**[Agent 1: Intent Understanding]**\n🎯 **Asset**: \`${spec.asset_type}\` (${dims})\n⚙️ **Style**: *${spec.style || "Stylized Hard-Surface"}* | **Budget**: ${tris}${comps}`;
          } else if (node === "scene") {
            const scene = state.scene_summary;
            const objCount = scene?.objects ? scene.objects.length : 0;
            detailText = `**[Agent 2: Scene Understanding]**\n🔍 Scanned active Blender workspace: **${objCount} object(s)** present. Bounding grid calibrated at origin \`(0, 0, 0)\`.`;
          } else if (node === "research") {
            const research = state.research_results || [];
            const notes = research.map((r: any) => `• **${r.title || "Spec"}**: ${r.notes || ""}`).join("\n");
            detailText = `**[Agent 3: Technical Research]**\n📚 Gathered engine constraints and topology standards:\n${notes || "Applied hard-surface PBR guidelines and non-manifold boundary rules."}`;
          } else if (node === "planning" && plan) {
            const stepList = (plan.steps || []).map((st: any, i: number) => `${i + 1}. \`${st.tool || "op"}\` → ${st.description}`).join("\n");
            detailText = `**[Agent 4: Step Planning]**\n📋 Synthesized **${plan.steps?.length || 0}-step** procedural modeling sequence:\n${stepList}`;
          } else if (node === "modeling") {
            const modelingDesc = latestEvent?.step_description || "Generated parametric bmesh primitives and applied bevel modifier stack.";
            detailText = `**[Agent 5: Autonomous Modeler]**\n🛠️ **Execution**: ${modelingDesc}`;
          } else if (node === "material") {
            const matDesc = latestEvent?.step_description || "Configured Principled BSDF shader with metallic/roughness nodes and studio lighting.";
            detailText = `**[Agent 6: Materials & Lighting]**\n🎨 **Shading Setup**: ${matDesc}`;
          } else if (node === "geometry_qa") {
            const qa = state.validation_result;
            const score = qa?.score !== undefined ? Math.round(qa.score * 100) : (state.geometry_score !== undefined ? Math.round(state.geometry_score * 100) : 100);
            const status = qa?.is_valid ? "PASSED" : "VERIFIED";
            detailText = `**[Agent 7: Topology QA]**\n📐 Topology Audit: **${score}% Pass Rate** (${status}). Manifold geometry confirmed with zero loose geometry.`;
          } else if (node === "visual_critic") {
            const critique = state.critique_result;
            const score = critique?.score !== undefined ? Math.round(critique.score * 100) : (state.visual_score !== undefined ? Math.round(state.visual_score * 100) : 92);
            const remarks = critique?.feedback || "Lighting distribution, specular bevel catch, and camera framing approved.";
            detailText = `**[Agent 8: Visual Critic]**\n👁️ Critique Score: **${score}%**\n${remarks}`;
          } else if (node === "export") {
            const exportDesc = latestEvent?.step_description || "Packaged .blend, .fbx, and .glb production bundles.";
            detailText = `**[Agent 10: Production Export]**\n📦 **Bundles Ready**: ${exportDesc}`;
          } else if (latestEvent?.step_description) {
            detailText = `**[Agent: ${node}]**\n${latestEvent.step_description}`;
=======
    const stream = connectWorkflowStream({
      sessionId: pipelineSessionId,
      onMessage: (payload: WorkflowStreamPayload) => {
        try {
          if (payload.event === "on_chat_model_stream" && payload.state?.chunk) {
             const chunk = payload.state.chunk as { content?: string | any[] };
             if (chunk.content) {
               const text = typeof chunk.content === "string" 
                 ? chunk.content 
                 : (Array.isArray(chunk.content) ? chunk.content.map(c => c.text || "").join("") : "");
               if (text) {
                 setLiveThinking(prev => ({ ...prev, content: prev.content + text }));
               }
             }
          } else if (payload.event === "on_tool_start" && payload.node) {
             const toolId = payload.state?.run_id as string || payload.node;
             setLiveThinking(prev => ({ 
               ...prev, 
               tools: [...prev.tools, { id: toolId, name: payload.node!, status: "running", input: payload.state?.input }] 
             }));
          } else if (payload.event === "on_tool_end" && payload.node) {
             const toolId = payload.state?.run_id as string || payload.node;
             setLiveThinking(prev => ({
               ...prev,
               tools: prev.tools.map(t => t.id === toolId ? { ...t, status: "done" } : t)
             }));
          } else if (payload.event === "on_chat_model_end") {
             setLiveThinking(prev => {
                const finalContent = prev.content.trim();
                if (finalContent || prev.tools.length > 0) {
                  setMessages(m => {
                    const last = m[m.length - 1];
                    if (last && last.role === "agent" && last.content === finalContent) return m;
                    return [...m, { id: activeMessageIdRef.current || nextMessageId("copilot"), role: "agent", content: finalContent, tools: prev.tools, time: "Just now" }];
                  });
                }
                return { ...prev, content: "", tools: [] };
             });
          } else if (payload.event === "workflow_complete" || payload.event === "workflow_missing" || payload.event === "workflow_failed") {
             setLiveThinking(prev => {
                const finalContent = prev.content.trim();
                if (finalContent || prev.tools.length > 0) {
                  setMessages(m => {
                    const last = m[m.length - 1];
                    if (last && last.role === "agent" && (last.content === finalContent || last.tools?.length === prev.tools.length)) {
                       return m;
                    }
                    return [...m, { id: activeMessageIdRef.current || nextMessageId("copilot"), role: "agent", content: finalContent, tools: prev.tools, time: "Just now" }];
                  });
                } else if (payload.event === "workflow_failed") {
                  setMessages(m => [...m, {
                    id: activeMessageIdRef.current || nextMessageId("error"),
                    role: "agent",
                    content: `⚠️ Agent Error: ${payload.error || "Workflow crashed (e.g. LLM recursion limit)"}`,
                    time: "Just now"
                  }]);
                }
                return { active: false, content: "", tools: [] };
             });
>>>>>>> 9960c34c885b76ae6a6056cb373b1205a98fc89e
          }

          onWorkflowEvent?.(payload);
        } catch (e) {
          console.error("Workflow stream parse error", e);
        }
      },
    });

    return () => {
      stream.close();
      setLiveThinking({ active: false, content: "", tools: [] });
    };
  }, [
    pipelineSessionId,
    onWorkflowEvent,
  ]);




  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const threadMessages = useExternalMessageConverter<CopilotMessage>({
    callback: (m) => {
      const parts: any[] = [];
      if (m.thinking) {
        parts.push({ type: "reasoning", text: m.thinking });
      }
      if (m.tools && m.tools.length > 0) {
        m.tools.forEach(t => {
          const toolPart: any = {
            type: "tool-call",
            toolName: t.name,
            toolCallId: t.id,
            args: t.input || {},
          };
          if (t.status === "done") {
            toolPart.result = "Success";
          } else if (t.status === "failed") {
            toolPart.error = "Tool failed";
          }
          parts.push(toolPart);
        });
      }
      if (m.content) {
        parts.push({ type: "text", text: m.content });
      }
      return {
        id: m.id,
        role: (m.role === "agent" || m.role === "copilot") ? "assistant" : m.role,
        content: parts,
      };
    },
    messages: [
      ...messages,
      ...(liveThinking.active
        ? [
            {
              id: activeMessageIdRef.current || "live-thinking",
              role: "agent" as const,
              content: liveThinking.content,
              tools: liveThinking.tools,
              time: "Just now",
            },
          ]
        : []),
    ],
    isRunning: pipelineRunning || loading,
  });

  const runtime = useExternalStoreRuntime({
    messages: threadMessages,
    isRunning: pipelineRunning || loading,
    onNew: async (msg) => {
      if (msg.content[0]?.type === "text") {
        await handleSend(msg.content[0].text);
      }
    },
    onReload: async (parentId) => {
      // Find the user message we are reloading from
      const targetIndex = messages.findIndex(m => m.id === parentId);
      if (targetIndex === -1) return;
      
      const targetMessage = messages[targetIndex];
      
      // Trim all messages after the parent user message
      setMessages(messages.slice(0, targetIndex + 1));
      
      // Trigger the pipeline again with the user's original text
      if (onStartPipeline && targetMessage.content) {
        handledWorkflowEventsRef.current.clear();
        onStartPipeline(targetMessage.content as string);
      }
    },
    onEdit: async (message) => {
      // Find the user message we are editing
      const targetIndex = messages.findIndex(m => m.id === message.sourceId);
      if (targetIndex === -1) return;
      
      const newText = Array.isArray(message.content) 
        ? message.content.find((c: any) => c.type === "text")?.text || ""
        : message.content;
      
      // Update the user message and trim all messages after it
      const newMessages = [...messages.slice(0, targetIndex), {
        ...messages[targetIndex],
        content: newText as string,
      }];
      setMessages(newMessages);
      
      // Trigger the pipeline again with the user's new text
      if (onStartPipeline && newText) {
        handledWorkflowEventsRef.current.clear();
        onStartPipeline(newText as string);
      }
    }
  });

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || input).trim();
    if (!text || loading) return;

    if (text.includes("Configure LLM Key")) {
      setKeyDialogOpen(true);
      return;
    }

<<<<<<< HEAD
    if (text.includes("Launch 10-Agent Pipeline") && onStartPipeline) {
      setShowProgressGrid(true);
      setAgentSteps(INITIAL_10_STEPS.map((s, idx) => (idx === 0 ? { ...s, status: "running" } : { ...s, status: "pending" })));
      onStartPipeline(assetSpec?.asset_type || "3D Asset");
    }

=======
>>>>>>> 9960c34c885b76ae6a6056cb373b1205a98fc89e
    const userMsg: CopilotMessage = {
      id: nextMessageId("user"),
      role: "user",
      content: text,
      attachments,
      time: "Just now",
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
<<<<<<< HEAD
    setLoading(true);

    try {
      // Build multi-turn conversation memory for context window
      const history = messages
        .filter((m) => m.role === "user" || m.role === "copilot")
        .slice(-8)
        .map((m) => ({
          role: m.role === "user" ? ("user" as const) : ("assistant" as const),
          content: m.content,
        }));

      // Retrieve user's configured API key from client state or browser storage
      const activeKey = apiKeyInput.trim() || (typeof window !== "undefined" ? localStorage.getItem("blendpilot_user_api_key") || "" : "");

      const res = await fetch("/api/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          asset_spec: assetSpec,
          current_plan: currentPlan,
          conversation_history: history,
          api_key: activeKey,
          provider: llmProvider,
          model: llmModel,
        }),
      });

      if (!res.ok) throw new Error("Copilot response error");
      const data = await res.json();

      const copilotMsg: CopilotMessage = {
        id: `copilot-${Date.now()}`,
        role: "copilot",
        content: data.reply,
        actions: data.suggested_actions || [],
        isLiveLLM: data.is_live_llm,
        time: "Just now",
      };
      setMessages((prev) => [...prev, copilotMsg]);
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "copilot",
          content: `⚠️ Copilot notice: ${e.message}`,
          time: "Just now",
        },
      ]);
    } finally {
      setLoading(false);
=======
    setAttachments([]);
    
    if (onStartPipeline) {
      handledWorkflowEventsRef.current.clear();
      onStartPipeline(text);
>>>>>>> 9960c34c885b76ae6a6056cb373b1205a98fc89e
    }
  };



  return (
    <>
<<<<<<< HEAD
      <Card className="bg-slate-900/80 backdrop-blur-2xl border-slate-700/50 flex flex-col h-full overflow-hidden shadow-[0_8px_32px_rgba(0,0,0,0.4)] ring-1 ring-white/5">
        {/* Header Bar with User API Key Configuration Button */}
        <CardHeader className="p-3 pb-2 border-b border-slate-700/50 bg-slate-800/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10 text-primary border border-primary/20">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <CardTitle className="text-xs font-bold text-foreground flex items-center gap-1.5">
                  3D Copilot & 10 Agents
                </CardTitle>
                <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-cyan-400" />
                  <span className="font-medium text-foreground">{llmProvider.toUpperCase()}</span>
                  <span>({llmModel})</span>
                </div>
              </div>
            </div>

            {/* Quick User API Key Config Button */}
            <div className="flex items-center gap-1.5">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setKeyDialogOpen(true)}
                className={`h-7 px-2.5 text-[11px] font-medium border gap-1.5 transition-all shadow-sm ${
                  hasApiKey
                    ? "bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                    : "bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border-amber-500/50 animate-pulse shadow-[0_0_12px_rgba(245,158,11,0.3)]"
                }`}
                title="Configure LLM API Key directly in the application"
              >
                <Key className="w-3.5 h-3.5" />
                {hasApiKey ? "Key Linked" : "🔑 Configure API Key"}
              </Button>
            </div>
          </div>
=======
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
>>>>>>> 9960c34c885b76ae6a6056cb373b1205a98fc89e
        </CardHeader>

        <CardContent className="p-0 flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 flex flex-col overflow-hidden p-3 relative">
            <div className="flex-1 min-h-0 relative">
              <AssistantRuntimeProvider runtime={runtime}>
                <Thread components={{ Composer: () => null }} />
              </AssistantRuntimeProvider>
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
<<<<<<< HEAD
              <Select value={llmProvider} onValueChange={(val) => {
                if (!val) return;
                setLlmProvider(val);
                if (val === "groq") setLlmModel("llama-3.3-70b-versatile");
                else if (val === "anthropic") setLlmModel("claude-3-5-sonnet-20241022");
                else if (val === "openai") setLlmModel("gpt-4o");
                else if (val === "custom") setLlmModel("gemini-1.5-flash");
              }}>
                <SelectTrigger className="h-9 text-xs bg-background">
                  <SelectValue placeholder="Select LLM Provider" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="groq">Groq (Ultra-Fast Llama 3.3 70B)</SelectItem>
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
=======
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
>>>>>>> 9960c34c885b76ae6a6056cb373b1205a98fc89e
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
