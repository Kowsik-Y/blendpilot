"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Box } from "lucide-react";

export function InteractiveHeader() {
  const [scrolled, setScrolled] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [mouseX, setMouseX] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
      const totalScroll = document.documentElement.scrollHeight - window.innerHeight;
      if (totalScroll > 0) {
        setScrollProgress((window.scrollY / totalScroll) * 100);
      }
    };

    const handleMouseMove = (e: MouseEvent) => {
      // Normalize mouse position for subtle gradient shift
      setMouseX((e.clientX / window.innerWidth) * 100);
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("mousemove", handleMouseMove, { passive: true });

    return () => {
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 w-full px-6 py-4 flex items-center justify-between z-50 transition-all duration-300 ${
        scrolled
          ? "bg-background/80 backdrop-blur-xl border-b border-border/50 shadow-lg shadow-black/10"
          : "bg-background/20 backdrop-blur-md border-b border-border/20"
      }`}
    >
      {/* Scroll Progress Bar at the bottom edge */}
      <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-border/20 overflow-hidden pointer-events-none">
        <div
          className="h-full bg-gradient-to-r from-cyan-500 via-violet-500 to-orange-500 transition-all duration-150 ease-out shadow-[0_0_8px_rgba(6,182,212,0.6)]"
          style={{ width: `${scrollProgress}%` }}
        />
      </div>

      <Link href="/" className="flex items-center gap-3 group">
        <div className="relative p-2 rounded-xl bg-gradient-to-br from-cyan-500 to-violet-600 text-white shadow-md transition-all duration-300 group-hover:shadow-lg group-hover:shadow-cyan-500/20">
          <Box className="w-5 h-5 transition-transform duration-300 group-hover:rotate-12" />
        </div>
        <span className="font-bold tracking-tight text-base text-foreground transition-colors group-hover:text-cyan-400">
          BlendPilot
        </span>
      </Link>

      <div className="flex items-center gap-3">
        <Link href="/login">
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground hover:text-foreground"
          >
            Sign In
          </Button>
        </Link>
        <Link href="/register">
          <Button
            size="sm"
            className="bg-primary text-primary-foreground hover:bg-primary/90 transition-all duration-300"
          >
            Get Started
          </Button>
        </Link>
      </div>
    </header>
  );
}
