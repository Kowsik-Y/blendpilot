"use client";

import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Circle, Loader2, Cpu } from "lucide-react";

export interface AgentStepInfo {
  id: string;
  name: string;
  desc: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "ERROR";
}

export const AGENT_DEFINITIONS: Array<{ id: string; name: string; desc: string }> = [
  { id: "intent", name: "1. Intent Understanding", desc: "Design intent & constraints" },
  { id: "scene", name: "2. Scene Understanding", desc: "Blender scene inspection" },
  { id: "research", name: "3. Technical Research", desc: "Engine topology rules" },
  { id: "planning", name: "4. Step Planning", desc: "Atomic modeling plan" },
  { id: "modeling", name: "5. Autonomous Modeling", desc: "Meshes, booleans, modifiers" },
  { id: "material", name: "6. Materials & Lighting", desc: "PBR nodes & studio lights" },
  { id: "geometry_qa", name: "7. Geometry QA", desc: "Deterministic topology QA" },
  { id: "visual_critic", name: "8. Visual Critic", desc: "Vision aesthetic critique" },
  { id: "human_feedback", name: "9. Human Review", desc: "Review & revisions gate" },
  { id: "export", name: "10. Production Export", desc: "Multi-format packaging" },
];

interface AgentTimelineProps {
  activeNode?: string | null;
  completedNodes?: string[];
}

export function AgentTimeline({ activeNode, completedNodes = [] }: AgentTimelineProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between pb-2 border-b border-border">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-primary" />
          10-Agent Pipeline Timeline
        </span>
        <Badge variant="outline" className="text-[10px] px-2 py-0 border-primary/30 text-primary">
          LangGraph
        </Badge>
      </div>

      <div className="space-y-1.5 max-h-95 overflow-y-auto pr-1">
        {AGENT_DEFINITIONS.map((agent, index) => {
          const isCompleted = completedNodes.includes(agent.id);
          const isRunning = activeNode === agent.id;

          let statusText = "PENDING";
          let badgeClass = "bg-muted/40 text-muted-foreground border-transparent";
          let icon = <Circle className="w-3.5 h-3.5 text-muted-foreground/50" />;

          if (isCompleted) {
            statusText = "DONE";
            badgeClass = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
            icon = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
          } else if (isRunning) {
            statusText = "RUNNING";
            badgeClass = "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 animate-pulse";
            icon = <Loader2 className="w-3.5 h-3.5 text-cyan-400 animate-spin" />;
          }

          return (
            <div
              key={agent.id}
              className={`p-2 rounded-xl border transition-all flex items-center justify-between text-xs ${
                isRunning
                  ? "bg-cyan-950/20 border-cyan-500/40 shadow-sm"
                  : isCompleted
                  ? "bg-card/40 border-border/60"
                  : "bg-muted/10 border-transparent opacity-60"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                {icon}
                <div className="truncate">
                  <div className={`font-medium ${isRunning ? "text-cyan-300 font-semibold" : "text-foreground"}`}>
                    {agent.name}
                  </div>
                  <div className="text-[10px] text-muted-foreground truncate">{agent.desc}</div>
                </div>
              </div>

              <Badge variant="outline" className={`text-[10px] px-2 py-0.5 shrink-0 ${badgeClass}`}>
                {statusText}
              </Badge>
            </div>
          );
        })}
      </div>
    </div>
  );
}
