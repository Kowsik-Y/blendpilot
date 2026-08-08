"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  Box,
  Download,
} from "lucide-react";
import { ThreeViewport, type WorkflowSceneObject } from "@/components/studio/three-viewport";
import { HumanReviewModal } from "@/components/studio/human-review-modal";
import { CopilotChatbox } from "@/components/studio/copilot-chatbox";
import { connectWorkflowStream, type WorkflowStreamPayload } from "@/lib/workflow-stream";

interface StudioAssetSpec {
  asset_type: string;
  dimensions?: {
    width: number;
    depth: number;
    height: number;
  };
  triangle_limit?: number;
  materials?: string[];
}

interface WorkflowStatePayload {
  current_agent?: string;
  status?: string;
  design_spec?: StudioAssetSpec;
  geometry_score?: number;
  geometry_qa_status?: string;
  visual_score?: number;
  geometry_repair_count?: number;
  visual_revision_count?: number;
}

interface WorkflowStreamHandle {
  close: () => void;
}

const PROJECT_WORKFLOW_SESSIONS_KEY = "blendpilot:project-workflow-sessions:v1";

function readNumberTuple(value: unknown, fallback: [number, number, number]): [number, number, number] {
  if (!Array.isArray(value) || value.length < 3) return fallback;
  const numbers = value.slice(0, 3).map((item) => Number(item));
  if (numbers.some((item) => Number.isNaN(item))) return fallback;
  return [numbers[0], numbers[1], numbers[2]];
}

function readString(value: unknown, fallback = "") {
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

export default function StudioPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const workflowStreamRef = useRef<WorkflowStreamHandle | null>(null);
  const handledSceneEventsRef = useRef<Set<string>>(new Set());
  const [running, setRunning] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [completedNodes, setCompletedNodes] = useState<string[]>([]);


  const [assetSpec, setAssetSpec] = useState<StudioAssetSpec>({
    asset_type: "crate",
    dimensions: { width: 1.0, depth: 0.7, height: 0.6 },
  });
  const [sceneObjects, setSceneObjects] = useState<WorkflowSceneObject[]>([]);
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
    if (!promptToRun.trim()) return;

    setRunning(true);
    setActiveNode("intent");
    setCompletedNodes([]);
    setSceneObjects([]);
    handledSceneEventsRef.current.clear();
    workflowStreamRef.current?.close();
    workflowStreamRef.current = null;

    try {
      const res = await fetch("/api/pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_prompt: promptToRun,
          project_id: projectId,
          enable_human_interrupt: false,
        }),
      });

      const data = await res.json();
      if (!data.success) {
        throw new Error(data.error || "Failed to start workflow");
      }

      setSessionId(data.session_id);
      const sessions = JSON.parse(window.localStorage.getItem(PROJECT_WORKFLOW_SESSIONS_KEY) || "{}") as Record<string, string>;
      sessions[projectId] = data.session_id;
      window.localStorage.setItem(PROJECT_WORKFLOW_SESSIONS_KEY, JSON.stringify(sessions));
      connectStream(data.session_id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to start workflow";
      toast.error(`Workflow Error: ${message}`);
      setRunning(false);
      setActiveNode(null);
    }
  };

  const applyToolResultToViewport = useCallback((payload: WorkflowStreamPayload) => {
    const eventKey =
      typeof payload.event_id === "number"
        ? `event:${payload.event_id}`
        : `${payload.tool}:${payload.step_id}:${JSON.stringify(payload.parameters || {})}`;
    if (handledSceneEventsRef.current.has(eventKey)) {
      return;
    }
    handledSceneEventsRef.current.add(eventKey);

    const params = payload.parameters || {};
    const response = payload.response || {};
    const tool = payload.tool;

    if (tool === "create_primitive") {
      const name = readString(params.name, readString(response.object_name, "Object"));
      const object: WorkflowSceneObject = {
        name,
        primitiveType: readString(params.primitive_type, "cube"),
        dimensions: readNumberTuple(params.dimensions, [1, 1, 1]),
        location: readNumberTuple(params.location, [0, 0, 0]),
        rotation: readNumberTuple(params.rotation, [0, 0, 0]),
        modifiers: [],
      };
      setSceneObjects((prev) => [...prev.filter((item) => item.name !== name), object]);
      return;
    }

    if (tool === "duplicate_object") {
      const sourceName = readString(params.name);
      const newName = readString(params.new_name, readString(response.new_object, `${sourceName}_copy`));
      const offset = readNumberTuple(params.offset, [0, 0, 0]);
      setSceneObjects((prev) => {
        const source = prev.find((item) => item.name === sourceName);
        if (!source) return prev;
        const copy: WorkflowSceneObject = {
          ...source,
          name: newName,
          location: [
            source.location[0] + offset[0],
            source.location[1] + offset[1],
            source.location[2] + offset[2],
          ],
        };
        return [...prev.filter((item) => item.name !== newName), copy];
      });
      return;
    }

    if (tool === "set_transform") {
      const name = readString(params.name);
      setSceneObjects((prev) =>
        prev.map((item) =>
          item.name === name
            ? {
              ...item,
              location: params.location ? readNumberTuple(params.location, item.location) : item.location,
              rotation: params.rotation ? readNumberTuple(params.rotation, item.rotation || [0, 0, 0]) : item.rotation,
            }
            : item
        )
      );
      return;
    }

    if (tool === "add_modifier") {
      const name = readString(params.object_name);
      const modifier = readString(params.modifier_type);
      setSceneObjects((prev) =>
        prev.map((item) =>
          item.name === name
            ? { ...item, modifiers: [...(item.modifiers || []), modifier] }
            : item
        )
      );
      return;
    }

    if (tool === "assign_material") {
      const name = readString(params.object_name);
      const materialName = readString(params.material_name);
      setSceneObjects((prev) =>
        prev.map((item) =>
          item.name === name ? { ...item, materialName } : item
        )
      );
    }
  }, []);

  const handleWorkflowStreamPayload = useCallback((payload: WorkflowStreamPayload) => {
    const payloads =
      payload.event === "snapshot" && Array.isArray(payload.state?.stream_events)
        ? (payload.state.stream_events as WorkflowStreamPayload[])
        : [payload];

    payloads.forEach((currentPayload) => {
      const node = currentPayload.node;
      const state = (currentPayload.state || {}) as WorkflowStatePayload;

      if (currentPayload.event === "tool_start") {
        setActiveNode("modeling_agent");
      }

      if (currentPayload.event === "tool_result" && currentPayload.status === "COMPLETED") {
        applyToolResultToViewport(currentPayload);
      }

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

      if (state.current_agent === "human_feedback") {
        setHumanReviewOpen(true);
      }

      if (currentPayload.event === "workflow_complete" || state.status === "COMPLETED") {
        workflowStreamRef.current?.close();
        workflowStreamRef.current = null;
        setRunning(false);
        setActiveNode(null);
        toast.success("3D Asset generated successfully!");
      }
    });
  }, [applyToolResultToViewport]);

  const connectStream = useCallback((sid: string) => {
    const stream = connectWorkflowStream({
      sessionId: sid,
      onOpen: (transport) => {
        if (transport === "websocket") {
          toast.success("Live workflow socket connected");
        }
      },
      onFallback: () => {
        toast.warning("WebSocket reconnect failed. Using SSE fallback.");
      },
      onMessage: (payload: WorkflowStreamPayload) => {
        try {
          handleWorkflowStreamPayload(payload);
        } catch (e) {
          console.error("Workflow stream parse error", e);
        }
      },
      onClose: () => {
        setRunning(false);
        setActiveNode(null);
      },
    });
    workflowStreamRef.current = stream;
  }, [handleWorkflowStreamPayload]);

  useEffect(() => {
    workflowStreamRef.current?.close();
    workflowStreamRef.current = null;

    const sessions = JSON.parse(window.localStorage.getItem(PROJECT_WORKFLOW_SESSIONS_KEY) || "{}") as Record<string, string>;
    const restoredSessionId = sessions[projectId] || null;
    queueMicrotask(() => {
      setSessionId(restoredSessionId);
      setRunning(false);
      setActiveNode(null);
      setCompletedNodes([]);
      setSceneObjects([]);
    });
    if (restoredSessionId) {
      connectStream(restoredSessionId);
    }

    return () => {
      workflowStreamRef.current?.close();
      workflowStreamRef.current = null;
    };
  }, [projectId, connectStream]);

  const handleFeedbackSubmit = async (action: "APPROVE" | "REQUEST_CHANGE", feedbackText?: string) => {
    setHumanReviewOpen(false);

    if (!sessionId) return;
    try {
      await fetch(`/api/pipeline/${sessionId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, feedback_text: feedbackText }),
      });
      toast.success(action === "APPROVE" ? "Production export approved!" : "Revision requested");
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to submit feedback";
      toast.error(`Feedback error: ${message}`);
    }
  };

  const handleDownload = () => {
    const asset = assetSpec?.asset_type || "crate";
    window.open(`/api/export/${asset}/download`, "_blank");
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
                {running ? activeNode || "running" : "10-Agent Copilot"}
              </Badge>
            </h1>
            <p className="text-xs text-muted-foreground">
              {completedNodes.length > 0
                ? `${completedNodes.length} orchestration stages completed`
                : "Production-grade 3D Viewport with unified Copilot Chat & Agent Stream"}
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleDownload}
            className="text-xs border-border text-foreground gap-1.5 h-8 hover:border-cyan-500/50"
          >
            <Download className="w-3.5 h-3.5" />
            Download Package (.zip)
          </Button>
        </div>
      </div>

      {/* Main Studio 2-Column Split: Viewport (Left 7-cols) + Unified Copilot Chatbox (Right 5-cols) */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch overflow-hidden">
        {/* Left Column: Full-Height 3D Viewport (No bottom text box) */}
        <div className="lg:col-span-7 flex flex-col gap-3 min-w-0 h-full overflow-hidden">
          <div className="flex-1 min-h-0 flex flex-col">
            <ThreeViewport assetSpec={assetSpec} sceneObjects={sceneObjects} />
          </div>
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
              onWorkflowEvent={handleWorkflowStreamPayload}
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
