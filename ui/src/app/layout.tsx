import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import { SessionProvider } from "next-auth/react";
import { TooltipProvider } from "@/components/ui/tooltip";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "BlendPilot — Self-Correcting 3D Agent Copilot",
  description: "Natural-language AI copilot for low-poly and game-ready 3D modeling in Blender.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} antialiased bg-background text-foreground min-h-screen`}>
        <SessionProvider>
          <ThemeProvider
            attribute="class"
            defaultTheme="dark"
            enableSystem={false}
            disableTransitionOnChange
          >


            <TooltipProvider>
              {children}
            </TooltipProvider>
            <Toaster richColors position="top-right" />
          </ThemeProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
