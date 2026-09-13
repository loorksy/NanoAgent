import type { TradingTeamAgentWire } from "@/lib/trading/types";
import { cn } from "@/lib/utils";

interface TradingTeamPanelProps {
  agents: TradingTeamAgentWire[];
  teamMode?: string | null;
  compact?: boolean;
}

function statusMark(status: string): string {
  if (status === "done") return "✓";
  if (status === "failed") return "✗";
  return "…";
}

export function TradingTeamPanel({ agents, teamMode, compact = false }: TradingTeamPanelProps) {
  if (!agents.length) return null;

  const sorted = [...agents].sort((a, b) => (a.layer ?? 0) - (b.layer ?? 0));

  return (
    <div className="rounded-lg border bg-muted/20 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Team agents
        </h3>
        {teamMode ? (
          <span className="text-[10px] uppercase text-muted-foreground">{teamMode}</span>
        ) : null}
      </div>
      <ul className={cn("space-y-2", compact && "text-xs")}>
        {sorted.map((agent) => (
          <li key={agent.agentId} className="rounded-md border bg-card/60 p-2">
            <div className="flex items-start gap-2">
              <span aria-hidden="true" className="mt-0.5 w-4 text-center font-mono">
                {statusMark(agent.status)}
              </span>
              <div className="min-w-0 flex-1">
                <div className="font-medium">{agent.role}</div>
                {agent.summary && agent.status !== "running" ? (
                  <p className="mt-1 whitespace-pre-wrap text-muted-foreground">
                    {agent.summary}
                  </p>
                ) : null}
                {agent.status === "running" ? (
                  <p className="mt-1 text-muted-foreground">Running…</p>
                ) : null}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
