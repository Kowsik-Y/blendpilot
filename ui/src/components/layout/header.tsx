"use client";

import { signOut, useSession } from "next-auth/react";
import { ThemeToggle } from "./theme-toggle";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { LogOut, User, Sparkles } from "lucide-react";
import Link from "next/link";

export function Header() {
  const { data: session } = useSession();
  const userName = session?.user?.name || "Creator";
  const userInitials = userName
    .split(" ")
    .map((n: string) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <header className="h-14 border-b border-border bg-background/80 backdrop-blur-md px-4 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-muted border border-border text-foreground text-xs font-medium">
          <Sparkles className="w-3 h-3 text-primary animate-pulse" />
          <span>Blender Bridge Connected</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <ThemeToggle />

        <DropdownMenu>
          <DropdownMenuTrigger>
            <div className="relative h-8 w-8 rounded-full border border-border cursor-pointer">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-muted text-foreground text-xs font-medium">
                  {userInitials || "BP"}
                </AvatarFallback>
              </Avatar>
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56 bg-popover text-popover-foreground border-border" align="end">
            <DropdownMenuGroup>
              <DropdownMenuLabel className="font-normal flex gap-2">
                <div className="relative h-8 w-8 rounded-full border border-border cursor-pointer">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-muted text-foreground text-xs font-medium">
                      {userInitials || "BP"}
                    </AvatarFallback>
                  </Avatar>
                </div>
                <div className="flex flex-col space-y-1">

                  <p className="text-sm font-medium text-foreground leading-none">{userName}</p>
                  <p className="text-xs text-muted-foreground leading-none">{session?.user?.email}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-border" />
              <DropdownMenuItem>
                <Link href="/settings" className="flex items-center w-full cursor-pointer">
                  <User className="mr-2 h-4 w-4 text-muted-foreground" />
                  <span>LLM & Bridge Settings</span>
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator className="bg-border" />
              <DropdownMenuItem
                onClick={() => signOut({ callbackUrl: "/login" })}
                className="text-destructive focus:text-destructive cursor-pointer"
              >
                <LogOut className="mr-2 h-4 w-4" />
                <span>Sign out</span>
              </DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
