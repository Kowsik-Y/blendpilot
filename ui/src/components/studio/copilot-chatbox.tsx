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
}

interface LiveThinkingState {
  active: boolean;
  content: string;
  tools: { id: string; name: string; status: "running" | "done" | "failed" }[];
}

export function CopilotChatbox({
  assetSpec,
  onApplyAction,
  onStartPipeline,
  onWorkflowEvent,
  pipelineSessionId,
  pipelineRunning,
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

  const [liveThinking, setLiveThinking] = useState<LiveThinkingState>({
    active: false,
    content: "",
    tools: [],
  });
  const nextMessageId = (prefix: string) => {
    messageIdRef.current += 1;
    return `${prefix}-${messageIdRef.current}`;
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
    setLiveThinking({ active: true, content: "", tools: [] });

    const stream = connectWorkflowStream({
      sessionId: pipelineSessionId,
      onMessage: (payload: WorkflowStreamPayload) => {
        try {
          if (payload.event === "on_chat_model_stream" && payload.state?.chunk) {
             const chunk = payload.state.chunk as { content?: string };
             if (chunk.content) {
               setLiveThinking(prev => ({ ...prev, content: prev.content + chunk.content }));
             }
          } else if (payload.event === "on_tool_start" && payload.node) {
             const toolId = payload.state?.run_id as string || payload.node;
             setLiveThinking(prev => ({ 
               ...prev, 
               tools: [...prev.tools, { id: toolId, name: payload.node!, status: "running" }] 
             }));
          } else if (payload.event === "on_tool_end" && payload.node) {
             const toolId = payload.state?.run_id as string || payload.node;
             setLiveThinking(prev => ({
               ...prev,
               tools: prev.tools.map(t => t.id === toolId ? { ...t, status: "done" } : t)
             }));
          } else if (payload.event === "workflow_complete") {
             setLiveThinking(prev => {
                const finalContent = prev.content || "✨ 3D asset generation completed successfully.";
                setMessages(m => [...m, {
                  id: nextMessageId("copilot"),
                  role: "agent",
                  content: finalContent,
                  time: "Just now"
                }]);
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

                      {liveThinking.active && (
                        <MessageScrollerItem messageId="live-thinking" className="order-1 animate-in fade-in slide-in-from-bottom-2">
                          <Message align="start" className="my-2">
                            <MessageAvatar>
                              <div className="w-7 h-7 rounded-xl flex items-center justify-center shrink-0 shadow-sm mt-0.5 bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                                <Sparkles className="w-3.5 h-3.5" />
                              </div>
                            </MessageAvatar>
                            <MessageContent>
                              <Bubble variant="outline" align="start">
                                <BubbleContent>
                                  <div className="flex flex-col gap-3">
                                    <div className="text-xs font-semibold flex items-center gap-2 text-cyan-400">
                                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                      Agent is thinking...
                                    </div>
                                    {liveThinking.content && (
                                      <div className="prose prose-invert prose-xs max-w-none wrap-break-word">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                          {liveThinking.content}
                                        </ReactMarkdown>
                                      </div>
                                    )}
                                    {liveThinking.tools.length > 0 && (
                                      <div className="mt-2 border-t border-border/40 pt-2">
                                        <ChainOfThought autoCloseOnAllComplete={false}>
                                          <ChainOfThoughtTrigger icon={<BrainCircuit className="w-4 h-4" />}>
                                            Tool Execution Trace
                                          </ChainOfThoughtTrigger>
                                          <ChainOfThoughtContent>
                                            {liveThinking.tools.map((t, idx) => (
                                              <ChainOfThoughtStep key={idx} status={t.status === "done" ? "completed" : "running"}>
                                                <ChainOfThoughtStepTitle icon={<Wrench className="w-4 h-4" />}>{t.name}</ChainOfThoughtStepTitle>
                                              </ChainOfThoughtStep>
                                            ))}
                                          </ChainOfThoughtContent>
                                        </ChainOfThought>
                                      </div>
                                    )}
                                  </div>
                                </BubbleContent>
                              </Bubble>
                            </MessageContent>
                          </Message>
                        </MessageScrollerItem>
                      )}

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
