"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, RefreshCw, UserCheck } from "lucide-react";

interface HumanReviewProps {
  open: boolean;
  onSubmit: (action: "APPROVE" | "REQUEST_CHANGE", feedbackText?: string) => void;
}

export function HumanReviewModal({ open, onSubmit }: HumanReviewProps) {
  const [feedback, setFeedback] = useState("");

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <Card className="w-full max-w-lg bg-card/95 border-border shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-bold flex items-center gap-2 text-foreground">
              <UserCheck className="w-5 h-5 text-amber-400" />
              Human Review Gate (Step 9/10)
            </CardTitle>
            <Badge variant="outline" className="border-amber-500/30 text-amber-400 text-xs">
              Awaiting Decision
            </Badge>
          </div>
          <CardDescription className="text-xs text-muted-foreground mt-1">
            The autonomous modeling and visual critique pipeline has prepared a model candidate. Please inspect the 3D viewport and approve production export or request revisions.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground">Modification Instructions (Optional):</label>
            <Input
              placeholder="e.g., Make the tabletop thicker, or change emission color to orange..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              className="text-xs h-9"
            />
          </div>
        </CardContent>

        <CardFooter className="flex items-center justify-end gap-2 pt-2 border-t border-border">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onSubmit("REQUEST_CHANGE", feedback)}
            className="text-xs border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            Request Revision
          </Button>
          <Button
            size="sm"
            onClick={() => onSubmit("APPROVE", feedback)}
            className="text-xs bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
            Approve & Export
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
