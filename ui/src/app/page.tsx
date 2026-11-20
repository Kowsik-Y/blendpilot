import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Box,
  Cpu,
  Layers,
  CheckCircle2,
  ArrowRight,
  Zap,
  Shield,
  Eye,
  Sparkles,
} from "lucide-react";
import { Interactive3D } from "@/components/Interactive3D";
import {
  TypingPromptDemo,
  AnimatedCounter,
  FloatingBadge,
  PipelineVisualizer,
  ScrollReveal,
  InteractiveTechTicker,
  InteractiveSpotlightCard,
  LiveBpyTerminal,
} from "@/components/HeroAnimations";
import { InteractiveHeader } from "@/components/InteractiveHeader";

const row1Features = [
  {
    icon: Cpu,
    glowColor: "cyan" as const,
    iconClasses: "bg-cyan-500/10 border-cyan-500/10 text-cyan-400 group-hover:shadow-cyan-500/10",
    titleClasses: "group-hover:text-cyan-400",
    title: "BYO LLM & RAG Memory",
    description: "Use OpenAI GPT-4o, Anthropic Claude, or local Ollama models with AES-256 encrypted keys and augmented Blender Python API documentation.",
    delay: 0,
  },
  {
    icon: Layers,
    glowColor: "violet" as const,
    iconClasses: "bg-violet-500/10 border-violet-500/10 text-violet-400 group-hover:shadow-violet-500/10",
    titleClasses: "group-hover:text-violet-400",
    title: "Non-Destructive Workflows",
    description: "Maintains full modifier stacks (Bevel, Subsurf, Boolean), procedural PBR node trees, and automated checkpoint snapshots for instant rollbacks.",
    delay: 100,
  },
  {
    icon: CheckCircle2,
    glowColor: "orange" as const,
    iconClasses: "bg-orange-500/10 border-orange-500/10 text-orange-400 group-hover:shadow-orange-500/10",
    titleClasses: "group-hover:text-orange-400",
    title: "Self-Correcting Topology QA",
    description: "Automated manifold integrity checks, normal orientation verification, and polygon budget enforcement before exporting to GLTF/FBX.",
    delay: 200,
  },
];

const row2Features = [
  {
    icon: Eye,
    glowColor: "cyan" as const,
    iconClasses: "bg-cyan-500/10 border-cyan-500/10 text-cyan-400 group-hover:shadow-cyan-500/10",
    titleClasses: "group-hover:text-cyan-400",
    title: "Visual Critique & Self-Healing",
    description: "Multi-modal vision models render and critique each iteration. Detects visual anomalies, broken geometry, and material issues — then autonomously fixes them.",
    delay: 50,
  },
  {
    icon: Zap,
    glowColor: "violet" as const,
    iconClasses: "bg-violet-500/10 border-violet-500/10 text-violet-400 group-hover:shadow-violet-500/10",
    titleClasses: "group-hover:text-violet-400",
    title: "Real-Time Collaboration",
    description: "Watch the agent work in real-time through live render previews and step-by-step execution logs. Chat with the agent to refine results mid-generation.",
    delay: 150,
  },
];

const stats = [
  { end: 99, suffix: "%", label: "Manifold Accuracy" },
  { end: 50, suffix: "+", label: "Blender Operators" },
  { end: 3, suffix: "x", label: "Faster Than Manual" },
  { end: 5, suffix: "", label: "Export Formats" },
];

export default async function HomePage() {
  const session = await auth();

  if (session?.user) {
    redirect("/projects");
  }

  return (
    <div className="min-h-screen flex flex-col bg-background overflow-x-hidden">


      {/* Interactive Header */}
      <InteractiveHeader />

      {/* Hero Section */}
      <InteractiveSpotlightCard glowColor="violet" intensity={0.24} >
        <main className="flex-1">
            <section className="relative min-h-[90vh] flex flex-col items-center justify-center px-6 pt-28 pb-16 overflow-hidden">

              {/* Gradient overlays for depth */}
              <div className="absolute inset-0 bg-linear-to-b from-background via-transparent to-transparent pointer-events-none z-0" />
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-150 h-150 bg-cyan-500/15 rounded-full blur-[120px] pointer-events-none" />
              <div className="absolute bottom-0 left-1/4 w-100 h-100 bg-violet-500/15 rounded-full blur-[100px] pointer-events-none" />

              {/* Content */}
              <div className="relative z-10 max-w-5xl mx-auto text-center space-y-8">
                {/* Floating badges */}
                <div className="flex flex-wrap items-center justify-center gap-2">
                  <FloatingBadge delay={200}>
                    Self-Correcting Pipeline
                  </FloatingBadge>
                  <FloatingBadge delay={400}>
                    <Zap className="w-3 h-3 text-orange-400" />
                    Multi-Agent System
                  </FloatingBadge>
                  <FloatingBadge delay={600}>
                    <Shield className="w-3 h-3 text-violet-400" />
                    Production Ready
                  </FloatingBadge>
                </div>

                {/* Main heading with gradient */}
                <h1 className="text-4xl sm:text-5xl md:text-7xl font-extrabold max-w-4xl mx-auto leading-[1.1] tracking-tight">
                  <span className="text-foreground">Autonomous 3D</span>
                  <br />
                  <span className="bg-linear-to-r from-cyan-400 via-violet-400 to-orange-400 bg-clip-text text-transparent">
                    Asset Modeling
                  </span>
                  <br />
                  <span className="text-foreground">for Blender</span>
                </h1>

                {/* Subtitle */}
                <p className="text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
                  BlendPilot transforms natural language prompts into
                  production-ready Blender 3D models with automated topology
                  validation, PBR materials, and self-healing visual critique.
                </p>

                {/* CTA Buttons */}
                <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
                  <Link href="/register">
                    <Button
                      size="lg"
                      className="group bg-primary text-primary-foreground hover:bg-primary/90 gap-2 h-13 px-8 text-base font-semibold shadow-xl border-0 transition-all duration-300 "
                    >
                      Start Modeling Now
                      <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" />
                    </Button>
                  </Link>
                  <Link href="/login">
                    <Button
                      size="lg"
                      variant="outline"
                      className="border-border/50 text-foreground h-13 px-8 text-base transition-all duration-300  backdrop-blur-md bg-card/30 hover:bg-card/50"
                    >
                      Existing Account
                    </Button>
                  </Link>
                </div>

                {/* Typing Demo */}
                <div className="pt-6">
                  <TypingPromptDemo />
                </div>
              </div>
            </section>

            {/* Interactive Infinite Tech Marquee Scroller */}
            <section className="relative z-20">
              <InteractiveTechTicker />
            </section>

            {/* Pipeline Section */}
            <section className="relative px-6 py-20 border-t border-border/30">
              <div className="absolute inset-0 bg-linear-to-b from-transparent via-cyan-500/6 to-transparent pointer-events-none" />
              <div className="max-w-5xl mx-auto space-y-12 relative z-10">
                <ScrollReveal>
                  <div className="text-center space-y-3">
                    <h2 className="text-2xl sm:text-3xl font-bold text-foreground">
                      How It Works
                    </h2>
                    <p className="text-sm text-muted-foreground max-w-lg mx-auto">
                      From natural language to production-ready 3D — fully automated,
                      self-correcting pipeline
                    </p>
                  </div>
                </ScrollReveal>
                <ScrollReveal delay={150}>
                  <PipelineVisualizer />
                </ScrollReveal>

                {/* Live bpy code generator terminal */}
                <ScrollReveal delay={250}>
                  <div className="pt-4">
                    <LiveBpyTerminal />
                  </div>
                </ScrollReveal>
              </div>
            </section>

            {/* Stats Section */}
            <section className="px-6 py-16 border-t border-border/30">
              <div className="max-w-4xl mx-auto">
                <ScrollReveal>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-8">
                    {stats.map((stat, i) => (
                      <AnimatedCounter key={i} end={stat.end} suffix={stat.suffix} label={stat.label} />
                    ))}
                  </div>
                </ScrollReveal>
              </div>
            </section>

            {/* Feature Grid */}
            <section className="px-6 py-20 border-t border-border/30">
              <div className="max-w-5xl mx-auto space-y-12">
                <ScrollReveal>
                  <div className="text-center space-y-3">
                    <h2 className="text-2xl sm:text-3xl font-bold text-foreground">
                      Built for Professionals
                    </h2>
                    <p className="text-sm text-muted-foreground max-w-lg mx-auto">
                      Enterprise-grade 3D generation with full control over every step
                    </p>
                  </div>
                </ScrollReveal>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {row1Features.map((feature, i) => (
                    <ScrollReveal key={i} delay={feature.delay}>
                      <InteractiveSpotlightCard glowColor={feature.glowColor} intensity={0.4} className="p-6 space-y-4 h-full">
                        <div className={`p-3 rounded-xl border w-fit transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg ${feature.iconClasses}`}>
                          <feature.icon className="w-5 h-5" />
                        </div>
                        <h3 className={`text-base font-bold text-foreground mt-4 transition-colors ${feature.titleClasses}`}>
                          {feature.title}
                        </h3>
                        <p className="text-xs text-muted-foreground leading-relaxed mt-2 transition-colors group-hover:text-foreground/70">
                          {feature.description}
                        </p>
                      </InteractiveSpotlightCard>
                    </ScrollReveal>
                  ))}
                </div>

                {/* Second row of cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {row2Features.map((feature, i) => (
                    <ScrollReveal key={i} delay={feature.delay}>
                      <InteractiveSpotlightCard glowColor={feature.glowColor} intensity={0.5} className="p-6 space-y-4 h-full">
                        <div className="flex items-start gap-5">
                          <div className={`p-3 rounded-xl border shrink-0 transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg ${feature.iconClasses}`}>
                            <feature.icon className="w-5 h-5" />
                          </div>
                          <div>
                            <h3 className={`text-base font-bold text-foreground transition-colors ${feature.titleClasses}`}>
                              {feature.title}
                            </h3>
                            <p className="text-xs text-muted-foreground leading-relaxed mt-2 transition-colors group-hover:text-foreground/70">
                              {feature.description}
                            </p>
                          </div>
                        </div>
                      </InteractiveSpotlightCard>
                    </ScrollReveal>
                  ))}
                </div>
              </div>
            </section>

            {/* CTA Banner */}
            <section className="px-6 py-20 border-t border-border/30">
              <ScrollReveal>
                <div className="max-w-3xl mx-auto relative">
                  <div className="absolute -inset-8 rounded-3xl bg-linear-to-r from-cyan-500/15 via-violet-500/15 to-orange-500/15 blur-2xl" />
                  <div className="relative rounded-2xl bg-card/80 backdrop-blur-xl border border-border/50 p-10 text-center space-y-6 shadow-2xl">
                    <h2 className="text-2xl sm:text-3xl font-bold text-foreground">
                      Ready to{" "}
                      <span className="bg-linear-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">
                        transform
                      </span>{" "}
                      your 3D workflow?
                    </h2>
                    <p className="text-sm text-muted-foreground max-w-md mx-auto">
                      Start generating production-ready 3D assets in minutes. No
                      complex setup required.
                    </p>
                    <Link href="/register">
                      <Button
                        size="lg"
                        className="group bg-primary text-primary-foreground hover:bg-primary/90 gap-2 h-13 px-8 text-base font-semibold shadow-xl border-0 transition-all duration-300  mt-2"
                      >
                        Get Started for Free
                        <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" />
                      </Button>
                    </Link>
                  </div>
                </div>
              </ScrollReveal>
            </section>
        
        </main>
      </InteractiveSpotlightCard>

      {/* Footer */}
      <footer className="border-t border-border/30 py-8 px-6">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-linear-to-br from-cyan-500 to-violet-600 text-white">
              <Box className="w-3.5 h-3.5" />
            </div>
            <span className="text-sm font-semibold text-foreground">
              BlendPilot
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Advanced Agentic 3D Studio — Built for Blender
          </p>
        </div>
      </footer>

    </div>

  );
}
