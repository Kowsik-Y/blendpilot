import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Clock, RefreshCcw, History, FileDown } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export interface Checkpoint {
  name: string;
  path: string;
  time: string;
}

interface VersionHistoryProps {
  projectId: string;
  refreshTrigger?: number;
  onRestore: (path: string) => void;
}

export function VersionHistory({ projectId, refreshTrigger, onRestore }: VersionHistoryProps) {
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchCheckpoints = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/projects/${projectId}/checkpoints`);
      if (res.ok) {
        const data = await res.json();
        setCheckpoints(data.checkpoints || []);
      }
    } catch (e) {
      console.error("Failed to fetch checkpoints", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCheckpoints();
  }, [projectId, refreshTrigger]);

  return (
    <Card className="border-border/70 bg-card/80 backdrop-blur-xl shadow-lg h-full flex flex-col">
      <CardHeader className="pb-3 border-b border-border/50">
        <CardTitle className="text-sm flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-muted-foreground" />
            <span>Version History</span>
          </div>
          <Button 
            variant="ghost" 
            size="icon" 
            className="w-6 h-6 rounded-full" 
            onClick={fetchCheckpoints}
            title="Refresh"
          >
            <RefreshCcw className="w-3.5 h-3.5 text-muted-foreground" />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 overflow-y-auto p-0">
        {loading && checkpoints.length === 0 ? (
          <div className="p-4 text-xs text-muted-foreground animate-pulse">Loading history...</div>
        ) : checkpoints.length === 0 ? (
          <div className="p-6 text-center text-sm text-muted-foreground flex flex-col items-center gap-2">
            <Clock className="w-8 h-8 opacity-20" />
            <p>No checkpoints saved yet.</p>
            <p className="text-xs opacity-70">The agent will automatically save checkpoints at milestones.</p>
          </div>
        ) : (
          <div className="relative p-4 flex flex-col gap-4">
            <div className="absolute left-6 top-4 bottom-4 w-px bg-border/50"></div>
            {checkpoints.map((cp, idx) => (
              <div key={cp.name} className="relative pl-8 fade-in slide-in-from-bottom-2">
                <div className="absolute left-1.5 top-1.5 w-2 h-2 rounded-full bg-primary/50 ring-4 ring-background z-10"></div>
                <div className="flex flex-col gap-1.5 p-3 rounded-xl border border-border/60 bg-background/50 hover:bg-background/80 transition-colors">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-sm font-medium text-foreground break-all">{cp.name.replace(projectId + "_", "")}</span>
                    <Badge variant="secondary" className="text-[9px] uppercase">
                      {new Date(cp.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </Badge>
                  </div>
                  <div className="text-[10px] text-muted-foreground font-mono truncate" title={cp.path}>
                    {cp.path}
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="w-full mt-1 h-7 text-xs gap-1.5 group hover:border-cyan-500/50 hover:text-cyan-500"
                    onClick={() => onRestore(cp.path)}
                  >
                    <FileDown className="w-3.5 h-3.5 group-hover:scale-110 transition-transform" />
                    Restore Checkpoint
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
