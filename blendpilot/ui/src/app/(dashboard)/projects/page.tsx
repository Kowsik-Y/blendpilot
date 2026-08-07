"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { FolderKanban, Plus, MessageSquare, Box } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

interface ProjectItem {
  id: string;
  name: string;
  status: string;
  designSpec?: string;
  createdAt: string;
  sessions: Array<{ id: string; title: string }>;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [newProjectName, setNewProjectName] = useState("");
  const [openDialog, setOpenDialog] = useState(false);
  const [creating, setCreating] = useState(false);

  const fetchProjects = async () => {
    try {
      const res = await fetch("/api/projects");
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
      }
    } catch {
      toast.error("Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;

    setCreating(true);
    try {
      const res = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newProjectName.trim() }),
      });

      if (res.ok) {
        toast.success("Project created!");
        setNewProjectName("");
        setOpenDialog(false);
        fetchProjects();
      }
    } catch {
      toast.error("Failed to create project");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6 bg-background text-foreground">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">3D Design Projects</h1>
          <p className="text-sm text-muted-foreground">
            Manage your persistent Blender assets, specifications, and associated chat sessions.
          </p>
        </div>

        <Dialog open={openDialog} onOpenChange={setOpenDialog}>
          <DialogTrigger>
            <div className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 py-2 cursor-pointer shadow-sm">
              <Plus className="w-4 h-4" />
              New Project
            </div>
          </DialogTrigger>
          <DialogContent className="bg-card border-border text-card-foreground">
            <form onSubmit={handleCreateProject}>
              <DialogHeader>
                <DialogTitle>Create 3D Design Project</DialogTitle>
                <DialogDescription className="text-muted-foreground">
                  Group your design requests, 3D render previews, and export assets.
                </DialogDescription>
              </DialogHeader>
              <div className="py-4 space-y-2">
                <Label htmlFor="projName">Project Name</Label>
                <Input
                  id="projName"
                  placeholder="e.g. Medieval Tavern Props, Sci-Fi Station"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="bg-background border-input"
                  required
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={creating} className="bg-primary text-primary-foreground hover:bg-primary/90">
                  {creating ? "Creating..." : "Create Project"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {loading ? (
        <div className="p-8 text-center text-muted-foreground">Loading projects...</div>
      ) : projects.length === 0 ? (
        <Card className="border-border bg-card text-center py-12">
          <CardContent className="flex flex-col items-center space-y-3">
            <div className="p-4 rounded-2xl bg-muted border border-border text-foreground">
              <FolderKanban className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">No Projects Yet</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              Create a project to store your 3D asset specifications or start generating immediately in chat.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <Card key={p.id} className="border-border bg-card hover:border-foreground/20 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-base font-semibold text-foreground truncate pr-2">
                    {p.name}
                  </CardTitle>
                  <Badge variant="outline" className="text-xs bg-muted border-border text-muted-foreground">
                    {p.status}
                  </Badge>
                </div>
                <CardDescription className="text-xs text-muted-foreground">
                  Created {new Date(p.createdAt).toLocaleDateString()}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Associated Chats:</span>
                  <span className="font-mono text-foreground">{p.sessions.length}</span>
                </div>
                <div className="pt-2 border-t border-border flex items-center justify-between">
                  <Link
                    href="/chat"
                    className="inline-flex items-center gap-1.5 text-primary hover:underline font-medium"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    Open Chat
                  </Link>
                  <span className="text-muted-foreground flex items-center gap-1">
                    <Box className="w-3.5 h-3.5" />
                    Blender Ready
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
