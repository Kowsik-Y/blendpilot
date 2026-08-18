"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  MessageSquare,
  Plus,
  Settings,
  Box,
  FolderKanban,
  Trash2,
  Cpu,
} from "lucide-react";
import { toast } from "sonner";

interface ProjectItem {
  id: string;
  name: string;
}

export function AppSidebar() {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();
  const router = useRouter();

  const fetchProjects = async () => {
    try {
      const res = await fetch("/api/projects");
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
      }
    } catch {
      // Ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void Promise.resolve().then(fetchProjects);
  }, [pathname]);

  const handleNewChat = async () => {
    router.push(`/projects`);
  };

  const handleDeleteProject = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();

    try {
      const res = await fetch(`/api/projects/${id}`, { method: "DELETE" });
      if (res.ok) {
        setProjects((prev) => prev.filter((p) => p.id !== id));
        toast.success("Project deleted");
        if (pathname.includes(id)) {
          router.push("/projects");
        }
      }
    } catch {
      toast.error("Failed to delete project");
    }
  };

  return (
    <aside className="w-64 border-r border-sidebar-border bg-sidebar text-sidebar-foreground flex flex-col h-screen shrink-0">
      {/* Brand logo */}
      <div className="p-4 border-b border-sidebar-border flex items-center gap-3">
        <div className="p-2 rounded-xl bg-primary text-primary-foreground">
          <Box className="w-5 h-5" />
        </div>
        <div>
          <h2 className="font-bold text-sm tracking-tight text-sidebar-foreground">BlendPilot</h2>
          <p className="text-[11px] text-muted-foreground">Blender Copilot v0.1</p>
        </div>
      </div>

      {/* New chat action */}
      <div className="p-3">
        <Button
          onClick={handleNewChat}
          className="w-full justify-start gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
          size="sm"
        >
          <Plus className="w-4 h-4" />
          <span>New 3D Design</span>
        </Button>
      </div>

      {/* Navigation Links */}
      <div className="px-3 py-1 space-y-1">
        <Link
          href="/projects"
          className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${pathname.startsWith("/projects")
              ? "bg-sidebar-accent text-sidebar-accent-foreground font-semibold"
              : "text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
            }`}
        >
          <FolderKanban className="w-4 h-4" />
          <span>Projects</span>
        </Link>
      </div>

      {/* Recent Projects list */}
      <div className="px-4 pt-3 pb-1">
        <span className="text-[10px] font-semibold tracking-wider uppercase text-muted-foreground">
          Recent 3D Designs
        </span>
      </div>

      <ScrollArea className="flex-1 px-3">
        <div className="space-y-1 pb-4">
          {loading ? (
            <div className="p-3 text-xs text-muted-foreground italic">Loading projects...</div>
          ) : projects.length === 0 ? (
            <div className="p-3 text-xs text-muted-foreground">No projects yet. Click &quot;New 3D Design&quot; above!</div>
          ) : (
            projects.map((p) => {
              const active = pathname === `/studio/${p.id}`;
              return (
                <Link
                  key={p.id}
                  href={`/studio/${p.id}`}
                  className={`group relative flex items-center justify-between px-3 py-2 rounded-lg text-xs transition-all ${active
                      ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium border border-sidebar-border"
                      : "text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
                    }`}
                >
                  <span className="truncate pr-4">{p.name || "Untitled Design"}</span>
                  <button
                    onClick={(e) => handleDeleteProject(e, p.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-destructive rounded transition-opacity"
                    title="Delete project"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </Link>
              );
            })
          )}
        </div>
      </ScrollArea>

      {/* Footer Navigation (Settings) */}
      <div className="p-3 border-t border-sidebar-border space-y-1">
        <Link
          href="/settings"
          className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${pathname === "/settings"
              ? "bg-sidebar-accent text-sidebar-accent-foreground font-semibold"
              : "text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
            }`}
        >
          <Settings className="w-4 h-4" />
          <span>LLM & RAG Settings</span>
        </Link>
        <div className="px-3 py-1 flex items-center justify-between text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <Cpu className="w-3 h-3 text-primary" />
            RAG Online
          </span>
          <span>128k Tokens</span>
        </div>
      </div>
    </aside>
  );
}
