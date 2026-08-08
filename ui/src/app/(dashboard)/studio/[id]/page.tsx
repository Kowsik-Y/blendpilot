"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

function readNumber(value: unknown, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export default function StudioPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const workflowStreamRef = useRef<WorkflowStreamHandle | null>(null);
  const handledSceneEventsRef = useRef<Set<string>>(new Set());
  const liveWorkflowRef = useRef(false);
  const [running, setRunning] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [completedNodes, setCompletedNodes] = useState<string[]>([]);
  const [selectedObjectName, setSelectedObjectName] = useState<string | null>(null);
  const [rightPanelTab, setRightPanelTab] = useState<"chat" | "inspector">("chat");


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

  const resolvedSelectedObjectName =
    (selectedObjectName && sceneObjects.some((item) => item.name === selectedObjectName)
      ? selectedObjectName
      : sceneObjects[0]?.name) || null;
  const selectedObject = sceneObjects.find((item) => item.name === resolvedSelectedObjectName) || null;

  const updateSceneObject = useCallback(
    (name: string, updater: (item: WorkflowSceneObject) => WorkflowSceneObject) => {
      setSceneObjects((prev) => prev.map((item) => (item.name === name ? updater(item) : item)));
    },
    []
  );

  const updateSelectedObject = useCallback(
    (updater: (item: WorkflowSceneObject) => WorkflowSceneObject) => {
      if (!selectedObjectName) return;
      updateSceneObject(selectedObjectName, updater);
    },
    [selectedObjectName, updateSceneObject]
  );

  const handleStartPipeline = async (promptToRun: string) => {
    if (!promptToRun.trim()) return;

    liveWorkflowRef.current = true;
    setRunning(true);
    setActiveNode("intent");
    setCompletedNodes([]);
    setHumanReviewOpen(false);
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
      liveWorkflowRef.current = false;
    }
  };



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

      if (state.current_agent === "human_feedback" && liveWorkflowRef.current) {
        setHumanReviewOpen(true);
      }

      if (currentPayload.event === "workflow_complete" || state.status === "COMPLETED") {
        workflowStreamRef.current?.close();
        workflowStreamRef.current = null;
        setRunning(false);
        setActiveNode(null);
        liveWorkflowRef.current = false;
        toast.success("3D Asset generated successfully!");
      }
    });
  }, []);

  const connectStream = useCallback((sid: string) => {
    const stream = connectWorkflowStream({
      sessionId: sid,
      onOpen: (transport) => {
        if (transport === "websocket") {
          toast.success("Live workflow socket connected");
        }
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
        liveWorkflowRef.current = false;
      },
    });
    workflowStreamRef.current = stream;
  }, [handleWorkflowStreamPayload]);

  useEffect(() => {
    workflowStreamRef.current?.close();
    workflowStreamRef.current = null;
    queueMicrotask(() => {
      setSessionId(null);
      setRunning(false);
      setActiveNode(null);
      setCompletedNodes([]);
      setHumanReviewOpen(false);
      setSceneObjects([]);
    });

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

  const handleDuplicateSelected = () => {
    if (!selectedObject) return;
    const newName = `${selectedObject.name}_copy`;
    const copy: WorkflowSceneObject = {
      ...selectedObject,
      name: newName,
      location: [selectedObject.location[0] + 0.25, selectedObject.location[1] + 0.25, selectedObject.location[2]],
    };
    setSceneObjects((prev) => [...prev.filter((item) => item.name !== newName), copy]);
    setSelectedObjectName(newName);
  };

  const handleSelectObject = useCallback((name: string | null) => {
    setSelectedObjectName(name);
    if (name) {
      setRightPanelTab("inspector");
    }
  }, []);

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

      {/* Main Studio Workspace: viewport + editor rail + chat */}
      <div className="flex-1 grid grid-cols-1 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,0.95fr)] gap-4 items-stretch overflow-hidden">
        <div className="flex min-w-0 h-full flex-col gap-4 overflow-hidden">
          <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
            <ThreeViewport
              assetSpec={assetSpec}
              sceneObjects={sceneObjects}
              selectedObjectName={resolvedSelectedObjectName}
              onObjectSelect={handleSelectObject}
            />
          </div>

          <Card className="border-border/70 bg-card/80 backdrop-blur-xl shadow-lg">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center justify-between gap-2">
                <span>Live Workflow</span>
                <Badge variant="outline" className="text-[10px] uppercase tracking-[0.2em]">
                  {running ? activeNode || "running" : "idle"}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
              <div className="rounded-xl border border-border/60 bg-background/60 p-3">
                <div className="text-muted-foreground">Objects</div>
                <div className="mt-1 text-lg font-semibold text-foreground">{sceneObjects.length}</div>
              </div>
              <div className="rounded-xl border border-border/60 bg-background/60 p-3">
                <div className="text-muted-foreground">Completed</div>
                <div className="mt-1 text-lg font-semibold text-foreground">{completedNodes.length}</div>
              </div>
              <div className="rounded-xl border border-border/60 bg-background/60 p-3">
                <div className="text-muted-foreground">Geometry</div>
                <div className="mt-1 text-lg font-semibold text-foreground">{Math.round(qaState.geometryScore * 100)}%</div>
              </div>
              <div className="rounded-xl border border-border/60 bg-background/60 p-3">
                <div className="text-muted-foreground">Visual</div>
                <div className="mt-1 text-lg font-semibold text-foreground">{Math.round(qaState.visualScore * 100)}%</div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="flex min-w-0 h-full flex-col overflow-hidden">
          <Tabs
            value={rightPanelTab}
            onValueChange={(value) => setRightPanelTab(value as "chat" | "inspector")}
            className="h-full flex flex-col gap-3"
          >
            <TabsList className="w-full justify-start">
              <TabsTrigger value="chat">Chat</TabsTrigger>
              <TabsTrigger value="inspector">Scene Inspector</TabsTrigger>
            </TabsList>

            <TabsContent value="chat" className="min-h-0 flex-1 overflow-hidden">
              <div className="h-full min-h-0 overflow-hidden">
                <CopilotChatbox
                  key={projectId}
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
            </TabsContent>

            <TabsContent value="inspector" className="min-h-0 flex-1 overflow-hidden">
              <Card className="border-border/70 bg-card/80 backdrop-blur-xl shadow-lg h-full flex flex-col">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center justify-between gap-2">
                    <span>Scene Inspector</span>
                    <Badge variant="secondary" className="text-[10px]">
                      {selectedObject ? selectedObject.name : "No selection"}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-4 overflow-hidden flex-1 min-h-0">
                  <div className="max-h-40 overflow-auto rounded-xl border border-border/60 bg-background/60 p-2">
                    <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                      Scene Outliner
                    </div>
                    <div className="flex flex-col gap-1">
                      {sceneObjects.length === 0 ? (
                        <div className="px-2 py-3 text-sm text-muted-foreground">Waiting for workflow-generated geometry.</div>
                      ) : (
                        sceneObjects.map((object) => (
                          <Button
                            key={object.name}
                            type="button"
                            variant={object.name === resolvedSelectedObjectName ? "secondary" : "ghost"}
                            className="justify-start gap-2 text-left"
                            onClick={() => handleSelectObject(object.name)}
                          >
                            <span className="truncate">{object.name}</span>
                            <Badge variant="outline" className="ml-auto text-[10px]">
                              {object.primitiveType}
                            </Badge>
                          </Button>
                        ))
                      )}
                    </div>
                  </div>

                  {selectedObject ? (
                    <div className="flex flex-col gap-3 rounded-xl border border-border/60 bg-background/60 p-3 overflow-auto">
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-muted-foreground">Properties</div>
                          <div className="text-sm font-medium text-foreground">Selected object</div>
                        </div>
                        <Button type="button" variant="outline" size="sm" onClick={handleDuplicateSelected}>
                          Duplicate
                        </Button>
                      </div>

                      <div className="grid gap-3">
                        <div className="grid gap-1.5">
                          <label className="text-xs font-medium text-muted-foreground">Name</label>
                          <Input
                            value={selectedObject.name}
                            onChange={(event) => {
                              const nextName = event.target.value.trim();
                              if (!nextName) return;
                              updateSceneObject(selectedObject.name, (item) => ({ ...item, name: nextName }));
                              setSelectedObjectName(nextName);
                            }}
                          />
                        </div>

                        <div className="grid gap-1.5">
                          <label className="text-xs font-medium text-muted-foreground">Material</label>
                          <Input
                            value={selectedObject.materialName || ""}
                            onChange={(event) => updateSelectedObject((item) => ({ ...item, materialName: event.target.value }))}
                            placeholder="e.g. brushed_metal"
                          />
                        </div>

                        <div className="grid gap-2">
                          <label className="text-xs font-medium text-muted-foreground">Dimensions</label>
                          <div className="grid grid-cols-3 gap-2">
                            {["X", "Y", "Z"].map((axis, index) => (
                              <Input
                                key={axis}
                                inputMode="decimal"
                                value={selectedObject.dimensions[index]}
                                onChange={(event) => {
                                  const nextValue = readNumber(event.target.value, selectedObject.dimensions[index]);
                                  updateSelectedObject((item) => {
                                    const nextDimensions: [number, number, number] = [...item.dimensions] as [number, number, number];
                                    nextDimensions[index] = nextValue;
                                    return { ...item, dimensions: nextDimensions };
                                  });
                                }}
                              />
                            ))}
                          </div>
                        </div>

                        <div className="grid gap-2">
                          <label className="text-xs font-medium text-muted-foreground">Location</label>
                          <div className="grid grid-cols-3 gap-2">
                            {["X", "Y", "Z"].map((axis, index) => (
                              <Input
                                key={axis}
                                inputMode="decimal"
                                value={selectedObject.location[index]}
                                onChange={(event) => {
                                  const nextValue = readNumber(event.target.value, selectedObject.location[index]);
                                  updateSelectedObject((item) => {
                                    const nextLocation: [number, number, number] = [...item.location] as [number, number, number];
                                    nextLocation[index] = nextValue;
                                    return { ...item, location: nextLocation };
                                  });
                                }}
                              />
                            ))}
                          </div>
                        </div>

                        <div className="grid gap-2">
                          <label className="text-xs font-medium text-muted-foreground">Rotation</label>
                          <div className="grid grid-cols-3 gap-2">
                            {["X", "Y", "Z"].map((axis, index) => (
                              <Input
                                key={axis}
                                inputMode="decimal"
                                value={selectedObject.rotation?.[index] ?? 0}
                                onChange={(event) => {
                                  const nextValue = readNumber(event.target.value, selectedObject.rotation?.[index] ?? 0);
                                  updateSelectedObject((item) => {
                                    const nextRotation: [number, number, number] = [...(item.rotation || [0, 0, 0])] as [number, number, number];
                                    nextRotation[index] = nextValue;
                                    return { ...item, rotation: nextRotation };
                                  });
                                }}
                              />
                            ))}
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-2">
                          {(selectedObject.modifiers || []).length > 0 ? (
                            selectedObject.modifiers?.map((modifier) => (
                              <Badge key={modifier} variant="outline" className="text-[10px]">
                                {modifier}
                              </Badge>
                            ))
                          ) : (
                            <span className="text-xs text-muted-foreground">No modifiers assigned yet.</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-dashed border-border/60 bg-background/60 p-4 text-sm text-muted-foreground">
                      Select an object in the outliner or viewport to inspect and edit its properties.
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Human Review Modal Gate */}
      <HumanReviewModal open={humanReviewOpen} onSubmit={handleFeedbackSubmit} />
    </div>
  );
}
