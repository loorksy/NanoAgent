import { cn } from "@/lib/utils";
import type { TradingStageWire } from "@/lib/trading/types";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface AgentTraceDrawerProps {
  stages: TradingStageWire[];
  className?: string;
}

export function AgentTraceDrawer({ stages, className }: AgentTraceDrawerProps) {
  const [open, setOpen] = useState(false);
  if (!stages.length) return null;

  return (
    <div className={cn("rounded-lg border border-border/60 bg-muted/20", className)}>
      <button
        type="button"
        className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-medium"
        onClick={() => setOpen((value) => !value)}
      >
        <span>Agent trace ({stages.length})</span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open ? (
        <ol className="max-h-48 space-y-1 overflow-y-auto border-t border-border/50 px-3 py-2 text-xs">
          {stages.map((stage, index) => (
            <li key={`${stage.stage}-${index}`} className="flex items-center gap-2">
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  stage.status === "done" ? "bg-emerald-400" : stage.status === "failed" ? "bg-rose-400" : "bg-amber-400",
                )}
              />
              <span className="font-medium">{stage.stage}</span>
              <span className="text-muted-foreground">{stage.status}</span>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}
