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

  // User LLM Settings loaded from Settings Store (/api/settings)
  const [llmProvider, setLlmProvider] = useState<string>("openai");
  const [llmModel, setLlmModel] = useState<string>("gpt-4o");
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

  const activeMessageIdRef = useRef<string | null>(null);

  // Listen to live pipeline WebSocket stream and update in-chat Agent Progress & Thought Bubbles
  useEffect(() => {
    if (!pipelineSessionId) return;

    handledWorkflowEventsRef.current.clear();
    activeMessageIdRef.current = nextMessageId("copilot");
    setLiveThinking({ active: true, content: "", tools: [] });

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
    
    if (onStartPipeline) {
      handledWorkflowEventsRef.current.clear();
      onStartPipeline(text);
    }
  };



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
