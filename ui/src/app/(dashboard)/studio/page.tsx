"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  Box,
  Download,
  Sparkles,
  Layers,
  Cpu,
  Sliders,
  CheckCircle2,
  FileCode,
  Bot,
} from "lucide-react";
import { ThreeViewport } from "@/components/studio/three-viewport";
import { QAMetricsCard } from "@/components/studio/qa-metrics-card";
import { HumanReviewModal } from "@/components/studio/human-review-modal";
import { CopilotChatbox } from "@/components/studio/copilot-chatbox";

const PRESETS = [
  {
    label: "📦 Sci-Fi Crate",
    prompt: "Create a low-poly sci-fi supply crate for Unity. Dimensions: 1.0m x 0.7m x 0.6m. Under 8,000 triangles. Dark metal with blue emissive strips.",
  },
  {
    label: "🪑 Dining Table",
    prompt: "Create a wooden dining table for Unity. Dimensions: 1.2m x 0.8m x 0.75m. Triangle limit: 5,000. Stylized wood finish.",
  },
  {
    label: "🛢️ Medieval Barrel",
    prompt: "Create a medieval wooden barrel with metal hoops. Dimensions: 0.5m x 0.5m x 0.8m. Triangle budget: 4,000.",
  },
  {
    label: "⚡ Energy Pylon",
    prompt: "Create a sci-fi energy pylon tower. Dimensions: 0.6m x 0.6m x 2.2m. Under 9,000 triangles. Glowing core.",
  },
];

const API_BASE = "http://localhost:8000";

export default function StudioPage() {
  const [running, setRunning] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [completedNodes, setCompletedNodes] = useState<string[]>([]);
  
  // Collapsible QA Metrics Drawer
  const [metricsOpen, setMetricsOpen] = useState(false);

  const [assetSpec, setAssetSpec] = useState<any>({
    asset_type: "crate",
    dimensions: { width: 1.0, depth: 0.7, height: 0.6 },
  });
  const [qaState, setQaState] = useState<{
    geometryScore: number;
    geometryStatus: string;
    visualScore: number;
    repairCount: number;
    revisionCount: number;
  }>({
    geometryScore: 1.0,
    geometryStatus: "READY",
    visualScore: 0.88,
    repairCount: 0,
    revisionCount: 0,
  });
  const [humanReviewOpen, setHumanReviewOpen] = useState(false);

  const handleStartPipeline = async (promptToRun: string) => {
    if (!promptToRun.trim() || running) return;

    setRunning(true);
    setActiveNode("intent");
    setCompletedNodes([]);

    try {
      const userApiKey = typeof window !== "undefined" ? localStorage.getItem("blendpilot_user_api_key") || "" : "";
      const userProvider = typeof window !== "undefined" ? localStorage.getItem("blendpilot_user_provider") || "groq" : "groq";

      const res = await fetch(`${API_BASE}/api/workflow/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_prompt: promptToRun,
          enable_human_interrupt: true,
          api_key: userApiKey,
          provider: userProvider,
        }),
      });

      const data = await res.json();
      if (!data.success) {
        throw new Error(data.error || "Failed to start workflow");
      }

      setSessionId(data.session_id);
      connectStream(data.session_id);
    } catch (err: any) {
      toast.error(`Workflow Error: ${err.message}`);
      setRunning(false);
      setActiveNode(null);
    }
  };

  const connectStream = (sid: string) => {
    const eventSource = new EventSource(`${API_BASE}/api/workflow/${sid}/stream`);

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const node = payload.node;
        const state = payload.state || {};

        if (node) {
          setCompletedNodes((prev) => (prev.includes(node) ? prev : [...prev, node]));
          setActiveNode(state.current_agent || null);
        }

        if (state.design_spec) {
          setAssetSpec(state.design_spec);
        }

        if (state.geometry_score !== undefined || state.visual_score !== undefined) {
          setQaState({
            geometryScore: state.geometry_score ?? 1.0,
            geometryStatus: state.geometry_qa_status ?? "PASS",
            visualScore: state.visual_score ?? 0.88,
            repairCount: state.geometry_repair_count ?? 0,
            revisionCount: state.visual_revision_count ?? 0,
          });
        }

        if (node === "visual_critic") {
          setHumanReviewOpen(true);
        }

        if (state.status === "COMPLETED" || payload.status === "COMPLETED") {
          eventSource.close();
          setRunning(false);
          setActiveNode(null);
          toast.success("3D Asset generated successfully!");
        }
      } catch (e) {
        console.error("SSE parse error", e);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setRunning(false);
      setActiveNode(null);
    };
  };

  const handleFeedbackSubmit = async (action: "APPROVE" | "REQUEST_CHANGE", feedbackText?: string) => {
    setHumanReviewOpen(false);

    if (!sessionId) return;
    try {
      await fetch(`${API_BASE}/api/workflow/${sessionId}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, feedback_text: feedbackText }),
      });
      toast.success(action === "APPROVE" ? "Production export approved!" : "Revision requested");
    } catch (e: any) {
      toast.error(`Feedback error: ${e.message}`);
    }
  };

  const handleDownload = (ext: "zip" | "blend" | "fbx" | "glb") => {
    const asset = assetSpec?.asset_type || "crate";
    window.open(`${API_BASE}/api/export/${asset}/download`, "_blank");
    toast.success(`Downloading ${asset} bundle`);
  };

  return (
    <div className="h-full flex flex-col gap-3 p-4 sm:p-6 min-h-[calc(100vh-4rem)]">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-primary text-primary-foreground shadow-md">
            <Box className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
              BlendPilot 3D Studio
              <Badge variant="outline" className="text-xs bg-cyan-500/10 text-cyan-400 border-cyan-500/30">
                10-Agent Copilot
              </Badge>
            </h1>
            <p className="text-xs text-muted-foreground">
              Production-grade 3D Viewport with unified Copilot Chat & Agent Stream
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
            onClick={() => setMetricsOpen((prev) => !prev)}
            title="Toggle QA Telemetry Drawer"
          >
            <Sliders className="w-3.5 h-3.5 mr-1 text-cyan-400" />
            <span>QA Metrics</span>
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => handleDownload("zip")}
            className="text-xs border-border text-foreground gap-1.5 h-8 hover:border-cyan-500/50"
          >
            <Download className="w-3.5 h-3.5" />
            Download Package (.zip)
          </Button>
        </div>
      </div>

      {/* Quick Presets Bar */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground font-medium flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-primary" /> Presets:
        </span>
        {PRESETS.map((p, idx) => (
          <button
            key={idx}
            onClick={() => handleStartPipeline(p.prompt)}
            className="text-xs px-2.5 py-1 rounded-lg bg-card border border-border hover:border-primary/50 text-foreground transition-all hover:bg-muted/30"
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Main Studio 2-Column Split: Viewport (Left 7-cols) + Unified Copilot Chatbox (Right 5-cols) */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch overflow-hidden">
        {/* Left Column: Full-Height 3D Viewport (No bottom text box) */}
        <div className="lg:col-span-7 flex flex-col gap-3 min-w-0 h-full">
          <div className="flex-1 min-h-[500px] h-full flex flex-col">
            <ThreeViewport assetSpec={assetSpec} />
          </div>

          {/* Optional Collapsible Metrics Drawer */}
          {metricsOpen && (
            <div className="animate-in fade-in duration-200">
              <QAMetricsCard
                geometryScore={qaState.geometryScore}
                geometryStatus={qaState.geometryStatus}
                visualScore={qaState.visualScore}
                repairCount={qaState.repairCount}
                revisionCount={qaState.revisionCount}
              />
            </div>
          )}
        </div>

        {/* Right Column: Unified Copilot Chatbox (All Prompts, Plans & Agents Flow Here) */}
        <div className="lg:col-span-5 flex flex-col gap-3 min-w-0 h-full overflow-hidden">
          <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
            <CopilotChatbox
              assetSpec={assetSpec}
              onApplyAction={(action) => {
                if (action.includes("Pipeline")) {
                  handleStartPipeline(
                    `Create a low-poly ${assetSpec?.asset_type || "sci-fi crate"} with beveled edges and PBR materials.`
                  );
                }
              }}
              onStartPipeline={(p) => handleStartPipeline(p)}
              pipelineSessionId={sessionId}
              pipelineRunning={running}
            />
          </div>


        </div>
      </div>

      {/* Human Review Modal Gate */}
      <HumanReviewModal open={humanReviewOpen} onSubmit={handleFeedbackSubmit} />
    </div>
  );
}
