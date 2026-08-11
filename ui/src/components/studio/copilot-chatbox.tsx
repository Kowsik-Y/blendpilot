"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
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
import { ComposerMenu, ComposerModelItem, ComposerModelTrigger } from "@/components/elements/composer";
import { Thread } from "@/components/assistant-ui/thread";
import {
  useExternalStoreRuntime,
  useExternalMessageConverter,
  AssistantRuntimeProvider,
  type ThreadMessageLike,
} from "@assistant-ui/react";
import { WebSearchToolUI, ResearchReportToolUI, ImageGenerationToolUI } from "@/components/assistant-ui/tools";
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
  ChevronDown,
} from "lucide-react";

export type CopilotAttachment = {
  id: string;
  name: string;
  type: string;
  url?: string;
};

export interface CopilotMessage {
  id: string;
  role: "user" | "assistant" | "agent" | "copilot";
  content: string | Record<string, any>;
  attachments?: CopilotAttachment[];
  time?: string;
  tools?: { id: string; name: string; status: "running" | "done" | "failed"; input?: any }[];
  thinking?: string;
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
  id?: string;
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
  const [hasTavilyApiKey, setHasTavilyApiKey] = useState<boolean>(false);
  
  const [availableModels, setAvailableModels] = useState<{id: string, name: string}[]>([]);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [modelPickerOpen, setModelPickerOpen] = useState(false);
  const modelPickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (modelPickerRef.current && !modelPickerRef.current.contains(event.target as Node)) {
        setModelPickerOpen(false);
      }
    }
    if (modelPickerOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    } else {
      document.removeEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [modelPickerOpen]);

  const [liveThinking, setLiveThinking] = useState<LiveThinkingState>({
    active: false,
    content: "",
    tools: [],
  });

  const nextMessageId = (prefix: string) => {
    return `${prefix}-${crypto.randomUUID()}`;
  };



  const loadSettings = async () => {
    try {
      const res = await fetch("/api/settings");
      if (res.ok) {
        const data = await res.json();
        setLlmProvider(data.llmProvider || "openai");
        setLlmModel(data.llmModel || "gpt-4o");
        setHasApiKey(data.hasApiKey || false);
        setHasTavilyApiKey(data.hasTavilyApiKey || false);
        
        // Fetch dynamic models in the background
        fetchModels(data.llmProvider || "openai", data.llmBaseUrl || "", data.llmApiKeyMasked || "");
      }
    } catch {
      // Fallback
    }
  };

  const fetchModels = async (prov: string, url: string, key: string) => {
    setFetchingModels(true);
    try {
      const res = await fetch("/api/models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: prov, baseUrl: url, apiKey: key }),
      });
      if (res.ok) {
        const data = await res.json();
        setAvailableModels(data.models || []);
      }
    } catch (e) {
      console.error("Failed to fetch models", e);
    } finally {
      setFetchingModels(false);
    }
  };

  const handleModelChange = async (newModel: string | null | any) => {
    if (!newModel || typeof newModel !== "string") return;
    setLlmModel(newModel);
    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ llmModel: newModel }),
      });
      if (res.ok) {
        toast.success(`Switched to ${newModel}`);
      }
    } catch {
      toast.error("Failed to save model preference");
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



  const activeMessageIdRef = useRef<string | null>(null);

  // Listen to live pipeline WebSocket stream and update in-chat Agent Progress & Thought Bubbles
  useEffect(() => {
    if (!pipelineSessionId) return;

    handledWorkflowEventsRef.current.clear();
    const newId = nextMessageId("copilot");
    activeMessageIdRef.current = newId;
    setLiveThinking({ active: true, id: newId, content: "", tools: [] });

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
                    const existingIdx = m.findIndex(msg => msg.id === activeMessageIdRef.current);
                    if (existingIdx !== -1) {
                       const newM = [...m];
                       newM[existingIdx] = { ...newM[existingIdx], content: finalContent, tools: prev.tools };
                       return newM;
                    }
                    return [...m, { id: activeMessageIdRef.current || nextMessageId("copilot"), role: "assistant", content: finalContent, tools: prev.tools, time: "Just now" }];
                  });
                }
                
                // Prepare a new ID for the NEXT turn of the model in the same workflow
                activeMessageIdRef.current = nextMessageId("copilot");
                
                return { active: true, id: activeMessageIdRef.current, content: "", tools: [] };
             });
          } else if (payload.event === "workflow_complete" || payload.event === "workflow_missing" || payload.event === "workflow_failed") {
             setLiveThinking(prev => {
                const finalContent = prev.content.trim();
                if (finalContent || prev.tools.length > 0) {
                  setMessages(m => {
                    const existingIdx = m.findIndex(msg => msg.id === activeMessageIdRef.current);
                    if (existingIdx !== -1) {
                       const newM = [...m];
                       newM[existingIdx] = { ...newM[existingIdx], content: finalContent, tools: prev.tools };
                       return newM;
                    }
                    return [...m, { id: activeMessageIdRef.current || nextMessageId("copilot"), role: "assistant", content: finalContent, tools: prev.tools, time: "Just now" }];
                  });
                } 
                
                if (payload.event === "workflow_failed") {
                  setMessages(m => [...m, {
                    id: nextMessageId("error"),
                    role: "assistant",
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

  const threadMessages = useExternalMessageConverter<any>({
    callback: (m) => {
      const parts: any[] = [];
      if (m.thinking) {
        parts.push({ type: "reasoning", text: m.thinking });
      }
      if (m.tools && m.tools.length > 0) {
        m.tools.forEach((t: any) => {
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
        let rewrittenContent = m.content as string;
        
        rewrittenContent = rewrittenContent.replace(
          /(^|[^\(])(\/(?:Users|home|tmp|var|mnt)[a-zA-Z0-9_.\-\/]+\.(?:png|jpe?g|gif|webp|svg))\b/gi,
          (match, prefix, pth) => `${prefix}\n\n![Preview](/api/local-image?path=${encodeURIComponent(pth)})\n\n`
        );
        
        rewrittenContent = rewrittenContent.replace(
          /!\[([^\]]*)\]\((\/[^\)]+\.(?:png|jpe?g|gif|webp|svg))\)/gi,
          (match, alt, pth) => {
            if (pth.startsWith('/api/')) return match;
            return `![${alt}](/api/local-image?path=${encodeURIComponent(pth)})`;
          }
        );
        
        parts.push({ type: "text", text: rewrittenContent });
      }
      
      // If there are parts, use them. Otherwise, if there is string content, use it. Otherwise, assistant-ui requires at least an empty text part.
      let finalContent = parts;
      if (parts.length === 0) {
          finalContent = [{ type: "text", text: m.content || "" }];
      }

      return {
        id: m.id,
        role: (m.role === "agent" || m.role === "copilot") ? "assistant" : m.role,
        content: finalContent,
      };
    },
    messages: [
      ...messages,
      ...(liveThinking.active
        ? [
            {
              id: liveThinking.id || "live-thinking",
              role: "assistant" as const,
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
      let text = "";
      if (typeof msg.content === "string") {
        text = msg.content;
      } else if (Array.isArray(msg.content)) {
        text = msg.content.find(c => c.type === "text")?.text || "";
      }
      
      const mappedAttachments = (msg.attachments as any)?.map((a: any) => ({
         id: a.id || crypto.randomUUID(),
         name: a.name,
         type: a.contentType || "application/octet-stream",
         url: a.url
      })) || [];
      
      await handleSend(text, mappedAttachments);
    },
    onReload: async (parentId) => {
      const targetIndex = messages.findIndex(m => m.id === parentId);
      if (targetIndex === -1) return;
      
      const targetMessage = messages[targetIndex];
      
      setMessages(messages.slice(0, targetIndex + 1));
      
      if (onStartPipeline && targetMessage.content) {
        handledWorkflowEventsRef.current.clear();
        onStartPipeline(targetMessage.content as string);
      }
    },
    onEdit: async (message) => {
      const targetIndex = messages.findIndex(m => m.id === message.sourceId);
      if (targetIndex === -1) return;
      
      const newText = Array.isArray(message.content) 
        ? message.content.find((c: any) => c.type === "text")?.text || ""
        : message.content;
      
      const newMessages = [...messages.slice(0, targetIndex), {
        ...messages[targetIndex],
        content: newText as string,
      }];
      setMessages(newMessages);
      
      if (onStartPipeline && newText) {
        handledWorkflowEventsRef.current.clear();
        onStartPipeline(newText as string);
      }
    }
  });

  const handleSend = async (textToSend?: string, customAttachments?: CopilotAttachment[]) => {
    const text = (textToSend || input).trim();
    if (!text || loading) return;

    const finalAttachments = customAttachments || attachments;

    const userMsg: CopilotMessage = {
      id: nextMessageId("user"),
      role: "user",
      content: text,
      attachments: finalAttachments,
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
      <Card className="py-0 flex flex-col h-full overflow-hidden">
        <CardContent className="p-0 flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 flex flex-col overflow-hidden p-3 relative bg-muted/20">
            <div className="flex-1 min-h-0 relative">
              <AssistantRuntimeProvider runtime={runtime}>
                <WebSearchToolUI />
                <ResearchReportToolUI />
                <ImageGenerationToolUI />
                <Thread
                  components={{
                    ComposerContextUsage: { 
                      system: 1.2, 
                      tools: 0.5, 
                      messages: (() => {
                        let chars = 0;
                        messages.forEach(m => {
                          if (typeof m.content === "string") chars += m.content.length;
                          else chars += JSON.stringify(m.content).length;
                          if (m.thinking) chars += m.thinking.length;
                          if (m.tools) chars += JSON.stringify(m.tools).length;
                        });
                        const tokens = chars / 4;
                        const kTokens = tokens / 1000;
                        return Math.max(0.1, parseFloat(kTokens.toFixed(1)));
                      })(),
                      total: (() => {
                        const name = (availableModels.find(m => m.id === llmModel)?.name || llmModel).toLowerCase();
                        if (name.includes("claude-3")) return 200;
                        if (name.includes("gpt-4")) return 128;
                        if (name.includes("gpt-3.5")) return 16;
                        if (name.includes("qwen") || name.includes("llama")) return 32;
                        return 128;
                      })()
                    },
                    ModelPicker: (
                      <div className="relative" ref={modelPickerRef}>
                        <ComposerMenu open={modelPickerOpen}>
                          {availableModels.length > 0 ? (
                            availableModels.map((m) => {
                              const entry = {
                                name: m.name,
                                meta: m.name.toLowerCase().includes("gpt") ? "OpenAI" : m.name.toLowerCase().includes("claude") ? "Anthropic" : "Local"
                              };
                              return (
                                <ComposerModelItem 
                                  key={m.id} 
                                  entry={entry} 
                                  selected={m.id === llmModel} 
                                  onClick={() => {
                                    handleModelChange(m.id);
                                    setModelPickerOpen(false);
                                  }} 
                                />
                              );
                            })
                          ) : (
                            <div className="px-2 py-2 text-xs text-muted-foreground">No models</div>
                          )}
                          <div className="px-2.5 py-1.5 border-t border-border mt-1">
                            <Link href="/settings" className="text-[11px] text-primary hover:underline flex items-center gap-1">
                              <Key className="w-3 h-3" />
                              Configure Keys
                            </Link>
                          </div>
                        </ComposerMenu>
                        <ComposerModelTrigger 
                          model={availableModels.find(m => m.id === llmModel)?.name || llmModel || "Select Model"} 
                          open={modelPickerOpen} 
                          onClick={() => setModelPickerOpen(!modelPickerOpen)} 
                        />
                      </div>
                    )
                  }}
                />
              </AssistantRuntimeProvider>
            </div>
          </div>
        </CardContent>
      </Card>
  );
}
function setKeyDialogOpen(arg0: boolean) {
  throw new Error("Function not implemented.");
}

