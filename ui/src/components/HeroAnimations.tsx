"use client";

import { useEffect, useState, useRef } from "react";
import {
  MessageSquare,
  BrainCircuit,
  Zap,
  ShieldCheck,
  PackageCheck,
  Box,
  Cpu,
  Layers,
  CheckCircle2,
  Terminal,
  FileCode,
  Eye,
  Sparkles,
  RefreshCw,
  Orbit,
} from "lucide-react";

// --- Typing prompt demo ---
const demoPrompts = [
  "Create a low-poly medieval castle with towers and a drawbridge",
  "Generate a sci-fi spaceship with PBR metallic materials",
  "Build a stylized forest scene with procedural trees",
  "Design a game-ready character base mesh with proper topology",
  "Model a steampunk clock tower with gears and pipes",
];

export function TypingPromptDemo() {
  const [currentPromptIndex, setCurrentPromptIndex] = useState(0);
  const [displayText, setDisplayText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const prompt = demoPrompts[currentPromptIndex];

    if (!isDeleting) {
      if (displayText.length < prompt.length) {
        timeoutRef.current = setTimeout(() => {
          setDisplayText(prompt.slice(0, displayText.length + 1));
        }, 35 + Math.random() * 25);
      } else {
        timeoutRef.current = setTimeout(() => setIsDeleting(true), 2000);
      }
    } else {
      if (displayText.length > 0) {
        timeoutRef.current = setTimeout(() => {
          setDisplayText(displayText.slice(0, -1));
        }, 15);
      } else {
        setIsDeleting(false);
        setCurrentPromptIndex((prev) => (prev + 1) % demoPrompts.length);
      }
    }

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [displayText, isDeleting, currentPromptIndex]);

  return (
    <div className="w-full max-w-2xl mx-auto relative group">
      <div className="absolute -inset-[1px] rounded-2xl bg-gradient-to-r from-cyan-500/30 via-violet-500/30 to-orange-500/30 blur-sm opacity-60 group-hover:opacity-100 transition-opacity duration-500" />
      <div className="relative rounded-2xl bg-card/80 backdrop-blur-xl border border-border/50 p-5 shadow-2xl">
        {/* Terminal-like header */}
        <div className="flex items-center gap-2 mb-3">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500/80" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
            <div className="w-3 h-3 rounded-full bg-green-500/80" />
          </div>
          <span className="text-[10px] text-muted-foreground/60 ml-2 font-mono tracking-wider uppercase">
            BlendPilot Agent
          </span>
        </div>

        {/* Prompt */}
        <div className="flex items-start gap-3">
          <span className="text-cyan-400 font-mono text-sm mt-0.5 shrink-0">
            ▸
          </span>
          <p className="text-sm text-foreground/90 font-mono leading-relaxed min-h-[2.5rem]">
            {displayText}
            <span className="inline-block w-[2px] h-4 bg-cyan-400 ml-[2px] align-middle animate-pulse" />
          </p>
        </div>

        {/* Status bar */}
        <div className="flex items-center gap-3 mt-3 pt-3 border-t border-border/30">
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <span className="text-[10px] text-muted-foreground/70 font-mono">
              Agent Ready
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-muted-foreground/50 font-mono">
              GPU: Blender 4.x
            </span>
          </div>
          <div className="flex items-center gap-1.5 ml-auto">
            <span className="text-[10px] text-cyan-400/60 font-mono">
              Multi-Agent Pipeline
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Animated counter ---
interface AnimatedCounterProps {
  end: number;
  suffix?: string;
  label: string;
  duration?: number;
}

export function AnimatedCounter({
  end,
  suffix = "",
  label,
  duration = 2000,
}: AnimatedCounterProps) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const hasAnimated = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true;
          const startTime = performance.now();

          const animate = (currentTime: number) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            setCount(Math.floor(eased * end));

            if (progress < 1) {
              requestAnimationFrame(animate);
            }
          };

          requestAnimationFrame(animate);
        }
      },
      { threshold: 0.3 }
    );

    if (ref.current) observer.observe(ref.current);

    return () => observer.disconnect();
  }, [end, duration]);

  return (
    <div ref={ref} className="text-center">
      <div className="text-3xl sm:text-4xl font-extrabold bg-gradient-to-r from-cyan-400 via-violet-400 to-orange-400 bg-clip-text text-transparent">
        {count}
        {suffix}
      </div>
      <div className="text-xs text-muted-foreground mt-1">{label}</div>
    </div>
  );
}

// --- Floating feature badge ---
interface FloatingBadgeProps {
  children: React.ReactNode;
  delay?: number;
}

export function FloatingBadge({ children, delay = 0 }: FloatingBadgeProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const timeout = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(timeout);
  }, [delay]);

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-card/60 backdrop-blur-md border border-border/50 text-[11px] text-muted-foreground font-medium transition-all duration-700 ${
        visible
          ? "opacity-100 translate-y-0"
          : "opacity-0 translate-y-3"
      }`}
    >
      {children}
    </span>
  );
}

// --- Pipeline step visualizer ---
const pipelineSteps = [
  {
    label: "Prompt",
    icon: MessageSquare,
    color: "from-cyan-500/20 to-cyan-500/5",
    activeBorder: "border-cyan-500/40 text-cyan-400",
    desc: "Natural language input parsed into structured 3D modeling intent",
  },
  {
    label: "Plan",
    icon: BrainCircuit,
    color: "from-violet-500/20 to-violet-500/5",
    activeBorder: "border-violet-500/40 text-violet-400",
    desc: "Multi-agent task decomposition & Blender Python script synthesis",
  },
  {
    label: "Generate",
    icon: Zap,
    color: "from-orange-500/20 to-orange-500/5",
    activeBorder: "border-orange-500/40 text-orange-400",
    desc: "Procedural geometry creation, modifier stacks & PBR shaders",
  },
  {
    label: "Validate",
    icon: ShieldCheck,
    color: "from-emerald-500/20 to-emerald-500/5",
    activeBorder: "border-emerald-500/40 text-emerald-400",
    desc: "Automated manifold checks, normal verification & topology QA",
  },
  {
    label: "Export",
    icon: PackageCheck,
    color: "from-blue-500/20 to-blue-500/5",
    activeBorder: "border-blue-500/40 text-blue-400",
    desc: "Production-ready GLTF, FBX, and native .blend asset export",
  },
];

export function PipelineVisualizer() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % pipelineSteps.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full max-w-3xl mx-auto space-y-6">
      <div className="flex items-start justify-between relative px-2">
        {/* Connection track & progress bar (precisely aligned to icon center at top-6 = 24px) */}
        <div className="absolute top-6 left-8 right-8 -translate-y-1/2 h-[2px] z-0">
          <div className="absolute inset-0 bg-border/50 rounded-full" />
          <div
            className="absolute left-0 top-0 bottom-0 bg-gradient-to-r from-cyan-500 via-violet-500 to-orange-500 rounded-full transition-all duration-700 ease-out shadow-[0_0_12px_rgba(6,182,212,0.4)]"
            style={{
              width: `${(activeStep / (pipelineSteps.length - 1)) * 100}%`,
            }}
          />
        </div>

        {pipelineSteps.map((step, i) => {
          const isActive = i === activeStep;
          const isPassed = i < activeStep;

          return (
            <button
              key={step.label}
              type="button"
              onClick={() => setActiveStep(i)}
              className="relative z-10 flex flex-col items-center gap-2 group cursor-pointer focus:outline-none transition-all duration-300"
            >
              {/* Icon Container with solid background so line stays cleanly behind */}
              <div
                className={`relative z-20 w-12 h-12 rounded-xl bg-card border flex items-center justify-center backdrop-blur-md shadow-md transition-all duration-500 ${
                  isActive
                    ? `ring-2 ring-primary/30 shadow-lg shadow-cyan-500/10 ${step.activeBorder} scale-105`
                    : isPassed
                    ? "border-border text-foreground/80"
                    : "border-border/40 text-muted-foreground/50 opacity-60 hover:opacity-100"
                }`}
              >
                {/* Gradient background layer */}
                <div
                  className={`absolute inset-0 rounded-xl bg-gradient-to-b ${step.color} transition-opacity duration-500 ${
                    isActive ? "opacity-100" : isPassed ? "opacity-40" : "opacity-0 group-hover:opacity-30"
                  }`}
                />
                <step.icon
                  className={`w-5 h-5 relative z-10 transition-colors duration-300 ${
                    isActive ? "text-foreground" : isPassed ? "text-foreground/80" : "text-muted-foreground/60"
                  }`}
                />
              </div>

              {/* Label */}
              <span
                className={`text-[11px] font-semibold tracking-wide transition-colors duration-300 ${
                  isActive
                    ? "text-foreground"
                    : isPassed
                    ? "text-foreground/70"
                    : "text-muted-foreground/40"
                }`}
              >
                {step.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Active step description badge */}
      <div className="text-center min-h-[24px]">
        <p className="text-xs text-muted-foreground transition-all duration-500 ease-in-out">
          <span className="font-semibold text-foreground mr-1.5">{pipelineSteps[activeStep].label}:</span>
          {pipelineSteps[activeStep].desc}
        </p>
      </div>
    </div>
  );
}

// --- Scroll Reveal Component ---
interface ScrollRevealProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}

export function ScrollReveal({ children, className = "", delay = 0 }: ScrollRevealProps) {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setTimeout(() => setIsVisible(true), delay);
          if (ref.current) observer.unobserve(ref.current);
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
    );

    if (ref.current) observer.observe(ref.current);

    return () => observer.disconnect();
  }, [delay]);

  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ease-out ${
        isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
      } ${className}`}
    >
      {children}
    </div>
  );
}

// --- Interactive Tech Ticker (Infinite Horizontal Scroller with Scroll Velocity) ---
const tickerItems = [
  { icon: Box, label: "Blender 4.x Python API", color: "text-cyan-400" },
  { icon: Cpu, label: "Multi-Model Orchestration", color: "text-violet-400" },
  { icon: Layers, label: "Procedural PBR Node Trees", color: "text-orange-400" },
  { icon: ShieldCheck, label: "Bevel & Subsurf Modifiers", color: "text-emerald-400" },
  { icon: Zap, label: "Visual Critique Self-Healing", color: "text-amber-400" },
  { icon: PackageCheck, label: "GLTF / FBX / OBJ / Blend Export", color: "text-blue-400" },
  { icon: CheckCircle2, label: "Manifold Topology QA", color: "text-cyan-400" },
  { icon: Terminal, label: "Local Ollama + GPT-4o / Claude", color: "text-violet-400" },
  { icon: FileCode, label: "Instant Checkpoint Snapshots", color: "text-orange-400" },
  { icon: Eye, label: "Automated Multi-Angle Renders", color: "text-emerald-400" },
];

export function InteractiveTechTicker() {
  const [isPaused, setIsPaused] = useState(false);

  return (
    <div
      className="w-full relative overflow-hidden py-4 border-y border-border/30 bg-card/20 backdrop-blur-md group select-none"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {/* Side gradient masks for seamless fade */}
      <div className="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-background to-transparent z-10 pointer-events-none" />
      <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-background to-transparent z-10 pointer-events-none" />

      <div
        className="flex items-center gap-4 whitespace-nowrap animate-ticker"
        style={{
          animationPlayState: isPaused ? "paused" : "running",
        }}
      >
        {/* Render 2 sets for seamless loop */}
        {[...tickerItems, ...tickerItems].map((item, idx) => (
          <div
            key={`${item.label}-${idx}`}
            className="inline-flex items-center gap-2.5 px-4 py-2 rounded-xl bg-card/60 border border-border/50 text-xs text-foreground/80 font-medium hover:border-cyan-500/40 hover:text-foreground hover:bg-card/90 transition-all duration-300 shadow-xs cursor-default shrink-0"
          >
            <item.icon className={`w-3.5 h-3.5 ${item.color}`} />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Interactive Spotlight Card ---
interface SpotlightCardProps {
  children: React.ReactNode;
  className?: string;
  glowColor?: "cyan" | "violet" | "orange";
}

export function InteractiveSpotlightCard({
  children,
  className = "",
  glowColor = "cyan",
}: SpotlightCardProps) {
  const divRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [opacity, setOpacity] = useState(0);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!divRef.current) return;
    const rect = divRef.current.getBoundingClientRect();
    setPosition({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const glowColors = {
    cyan: "rgba(6, 182, 212, 0.12)",
    violet: "rgba(139, 92, 246, 0.12)",
    orange: "rgba(249, 115, 22, 0.12)",
  };

  return (
    <div
      ref={divRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setOpacity(1)}
      onMouseLeave={() => setOpacity(0)}
      className={`relative overflow-hidden rounded-2xl bg-card/50 backdrop-blur-md border border-border/50 transition-all duration-500 hover:-translate-y-1 hover:shadow-2xl ${className}`}
    >
      {/* Spotlight mouse-tracking radial glow */}
      <div
        className="pointer-events-none absolute -inset-px rounded-2xl transition-opacity duration-300"
        style={{
          opacity,
          background: `radial-gradient(400px circle at ${position.x}px ${position.y}px, ${glowColors[glowColor]}, transparent 60%)`,
        }}
      />
      <div className="relative z-10">{children}</div>
    </div>
  );
}

// --- Live Blender Python Execution Terminal ---
const bpyCodeSnippets = [
  `import bpy\n\n# Autonomous 3D Mesh Synthesis\nbpy.ops.mesh.primitive_cylinder_add(radius=1.2, depth=3.0, vertices=32)\ncastle_tower = bpy.context.active_object\ncastle_tower.name = "Tower_Main"`,
  `# Non-Destructive Modifiers Stack\nbevel = castle_tower.modifiers.new(name="Bevel", type='BEVEL')\nbevel.width = 0.08\nbevel.segments = 3\n\nsubsurf = castle_tower.modifiers.new(name="Subdivision", type='SUBSURF')\nsubsurf.levels = 2`,
  `# Procedural Stone PBR Material Setup\nmat = bpy.data.materials.new(name="Medieval_Stone_PBR")\nmat.use_nodes = True\nbsdf = mat.node_tree.nodes["Principled BSDF"]\nbsdf.inputs["Roughness"].default_value = 0.85\n\n# Validation Status: 0 Non-Manifold Edges ✓`,
];

export function LiveBpyTerminal() {
  const [activeSnippetIndex, setActiveSnippetIndex] = useState(0);
  const [displayedCode, setDisplayedCode] = useState("");
  const [charIndex, setCharIndex] = useState(0);

  useEffect(() => {
    const currentSnippet = bpyCodeSnippets[activeSnippetIndex];

    if (charIndex < currentSnippet.length) {
      const timeout = setTimeout(() => {
        setDisplayedCode(currentSnippet.slice(0, charIndex + 1));
        setCharIndex((prev) => prev + 1);
      }, 18);
      return () => clearTimeout(timeout);
    } else {
      const timeout = setTimeout(() => {
        setCharIndex(0);
        setDisplayedCode("");
        setActiveSnippetIndex((prev) => (prev + 1) % bpyCodeSnippets.length);
      }, 3000);
      return () => clearTimeout(timeout);
    }
  }, [charIndex, activeSnippetIndex]);

  return (
    <div className="w-full max-w-2xl mx-auto rounded-2xl bg-card/90 backdrop-blur-xl border border-border/70 shadow-2xl overflow-hidden font-mono text-xs">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/40 bg-muted/40">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
          </div>
          <span className="text-[10px] text-muted-foreground ml-2 font-medium tracking-wide">
            blender_script_synthesizer.py
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Live Execution
          </span>
        </div>
      </div>

      {/* Code Body */}
      <div className="p-4 bg-background/50 min-h-[140px] text-foreground/90 overflow-x-auto leading-relaxed whitespace-pre-wrap">
        <code>
          {displayedCode}
          <span className="inline-block w-1.5 h-3.5 bg-cyan-400 ml-0.5 align-middle animate-pulse" />
        </code>
      </div>
    </div>
  );
}
