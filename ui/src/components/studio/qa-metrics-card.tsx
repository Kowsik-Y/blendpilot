"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ShieldCheck, Sparkles, RefreshCw, CheckCircle2, AlertTriangle } from "lucide-react";

interface QAMetricsProps {
  geometryScore?: number;
  geometryStatus?: string;
  visualScore?: number;
  repairCount?: number;
  revisionCount?: number;
}

export function QAMetricsCard({
  geometryScore = 1.0,
  geometryStatus = "PASS",
  visualScore = 0.88,
  repairCount = 0,
  revisionCount = 0,
}: QAMetricsProps) {
  const isPass = geometryStatus === "PASS" || geometryStatus === "PASSED";

  return (
    <Card className="bg-card/70 backdrop-blur-md border-border">
      <CardHeader className="p-3.5 pb-2">
        <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground flex items-center justify-between">
          <span className="flex items-center gap-1.5 font-semibold">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Quality & Verification
          </span>
          <Badge
            variant="outline"
            className={`text-[10px] ${
              isPass
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : "bg-amber-500/10 text-amber-400 border-amber-500/20"
            }`}
          >
            {geometryStatus}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-3.5 pt-0 space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2 rounded-xl bg-muted/20 border border-border/50">
            <div className="text-[11px] text-muted-foreground">Topology QA</div>
            <div className="text-lg font-bold text-emerald-400">
              {Math.round(geometryScore * 100)}%
            </div>
            <div className="text-[10px] text-muted-foreground flex items-center gap-1 mt-0.5">
              <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" /> Manifold Valid
            </div>
          </div>

          <div className="p-2 rounded-xl bg-muted/20 border border-border/50">
            <div className="text-[11px] text-muted-foreground">Visual Aesthetic</div>
            <div className="text-lg font-bold text-cyan-400">
              {Math.round(visualScore * 100)}%
            </div>
            <div className="text-[10px] text-muted-foreground flex items-center gap-1 mt-0.5">
              <Sparkles className="w-2.5 h-2.5 text-cyan-400" /> Multi-modal Critique
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between text-xs px-2 py-1.5 rounded-lg bg-muted/10 border border-border/40 text-muted-foreground">
          <span className="flex items-center gap-1">
            <RefreshCw className="w-3 h-3 text-primary" /> Autonomous Repair Loops
          </span>
          <span className="font-semibold text-foreground">
            {repairCount} QA / {revisionCount} Visual
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
