import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Box, Sparkles, Cpu, Layers, CheckCircle2, ArrowRight } from "lucide-react";

export default async function HomePage() {
  const session = await auth();

  if (session?.user) {
    redirect("/projects");
  }

  return (
    <div className="min-h-screen flex flex-col justify-between">
      {/* Navigation Header */}
      <header className="border-b border-border bg-background/80 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-primary text-primary-foreground">
            <Box className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold tracking-tight text-base text-foreground">BlendPilot AI</span>
            <span className="text-xs text-muted-foreground ml-2">Blender 4.x Copilot</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login">
            <Button variant="ghost" size="sm">
              Sign In
            </Button>
          </Link>
          <Link href="/register">
            <Button size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90">
              Get Started
            </Button>
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-5xl mx-auto px-6 py-16 text-center space-y-8 flex-1 flex flex-col items-center justify-center">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-muted border border-border text-xs text-muted-foreground font-medium">
          <Sparkles className="w-3.5 h-3.5 text-primary" />
          <span>Self-Correcting Multi-Agent 3D Pipeline</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight max-w-3xl leading-tight text-foreground">
          Autonomous 3D Asset Modeling for Blender 4.x
        </h1>

        <p className="text-lg text-muted-foreground max-w-2xl">
          BlendPilot AI transforms natural language prompts into production-ready Blender 3D models with automated topology validation, PBR materials, and self-healing visual critique.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
          <Link href="/register">
            <Button size="lg" className="bg-primary text-primary-foreground hover:bg-primary/90 gap-2 h-12 px-6 text-base font-semibold shadow-lg">
              Start Modeling Now <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
          <Link href="/login">
            <Button size="lg" variant="outline" className="border-border text-foreground h-12 px-6 text-base">
              Existing Account
            </Button>
          </Link>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-12 text-left w-full">
          <div className="p-6 rounded-2xl bg-card border border-border space-y-3">
            <div className="p-2.5 rounded-xl bg-muted border border-border text-foreground w-fit">
              <Cpu className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-foreground">BYO LLM & RAG Memory</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Use OpenAI GPT-4o, Anthropic Claude, or local Ollama models with AES-256 encrypted keys and augmented Blender Python API documentation.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-card border border-border space-y-3">
            <div className="p-2.5 rounded-xl bg-muted border border-border text-foreground w-fit">
              <Layers className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-foreground">Non-Destructive Workflows</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Maintains full modifier stacks (Bevel, Subsurf, Boolean), procedural PBR node trees, and automated checkpoint snapshots for instant rollbacks.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-card border border-border space-y-3">
            <div className="p-2.5 rounded-xl bg-muted border border-border text-foreground w-fit">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-foreground">Self-Correcting Topology QA</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Automated manifold integrity checks, normal orientation verification, and polygon budget enforcement before exporting to GLTF/FBX.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border py-6 px-6 text-center text-xs text-muted-foreground">
        <p>BlendPilot AI — Advanced Agentic 3D Studio. Built for Blender 4.x.</p>
      </footer>
    </div>
  );
}
