import { stageLabel as resolveStageLabel } from "@/lib/trading/stage-labels";
import type { TradingStageWire } from "@/lib/trading/types";
import { cn } from "@/lib/utils";

interface TradingStageChecklistProps {
  stages: TradingStageWire[];
  compact?: boolean;
  locale?: string | null;
}

function statusMark(status: string): string {
  if (status === "done") return "✓";
  if (status === "failed") return "✗";
  return "…";
}

export function TradingStageChecklist({
  stages,
  compact = false,
  locale,
}: TradingStageChecklistProps) {
  if (stages.length === 0) return null;
  return (
    <ul className={cn("space-y-1 text-sm", compact && "text-xs")}>
      {stages.map((row) => (
        <li
          key={row.stage}
          className={cn(
            "flex items-center gap-2",
            row.status === "failed" && "text-destructive",
            row.status === "running" && "text-muted-foreground",
          )}
        >
          <span aria-hidden="true" className="w-4 text-center font-mono">
            {statusMark(row.status)}
          </span>
          <span>{resolveStageLabel(row.stage, locale)}</span>
        </li>
      ))}
    </ul>
  );
}
