import { TradingOutcomeBanner } from "@/components/trading/TradingOutcomeBanner";
import { TradingRecommendationCard } from "@/components/trading/TradingRecommendationCard";
import { Button } from "@/components/ui/button";
import type { TradingOutcomeWire, TradingResultWire } from "@/lib/trading/types";
import { useClient } from "@/providers/ClientProvider";
import { useCallback, useEffect, useMemo, useState } from "react";

interface InboxRow {
  id: string;
  symbol: string;
  direction: string;
  entry: number | null;
  stop_loss: number | null;
  targets: number[];
  status: string;
  summary: string;
  confidence: number;
  created_at: number;
  paperAction?: string | null;
}

type InboxFilter = "all" | "open" | "closed";

const OPEN_STATUSES = new Set(["valid_now", "awaiting_activation", "waiting", "in_trade"]);
const CLOSED_STATUSES = new Set(["tp1", "invalidated", "expired"]);

function rowToResult(row: InboxRow): TradingResultWire {
  return {
    decision: row.direction,
    confidence: row.confidence,
    summary: row.summary,
    recommendationId: row.id,
    recommendation: {
      action: row.direction,
      entry: row.entry ?? undefined,
      stopLoss: row.stop_loss ?? undefined,
      targets: row.targets,
      executionState: row.status,
    },
    cards: [],
  };
}

function statusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

export function TradingInbox() {
  const { getToken } = useClient();
  const [rows, setRows] = useState<InboxRow[]>([]);
  const [alerts, setAlerts] = useState<TradingOutcomeWire[]>([]);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(() => new Set());
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<InboxRow | null>(null);
  const [filter, setFilter] = useState<InboxFilter>("all");

  const refresh = useCallback(async () => {
    const token = getToken();
    const res = await fetch("/api/trading/recommendations", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      setError("Failed to load recommendations");
      return;
    }
    const payload = await res.json() as {
      recommendations: InboxRow[];
      recentOutcomeAlerts?: TradingOutcomeWire[];
    };
    setRows(payload.recommendations ?? []);
    setAlerts(payload.recentOutcomeAlerts ?? []);
    setError(null);
  }, [getToken]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 60_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const filteredRows = useMemo(() => {
    if (filter === "open") {
      return rows.filter((row) => OPEN_STATUSES.has(row.status));
    }
    if (filter === "closed") {
      return rows.filter((row) => CLOSED_STATUSES.has(row.status));
    }
    return rows;
  }, [filter, rows]);

  const visibleAlerts = alerts.filter(
    (alert) => !dismissedAlerts.has(`${alert.recommendationId}-${alert.outcomeStatus}`),
  );

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 p-4 sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Recommendations</h1>
          <p className="text-sm text-muted-foreground">
            Stored gold recommendations with live outcome status and paper actions
          </p>
        </div>
        <Button variant="outline" onClick={() => void refresh()}>Refresh</Button>
      </div>
      {visibleAlerts.length > 0 ? (
        <TradingOutcomeBanner
          alerts={visibleAlerts}
          onDismiss={(key) => {
            setDismissedAlerts((current) => new Set(current).add(key));
          }}
        />
      ) : null}
      <div className="flex gap-2">
        {(["all", "open", "closed"] as InboxFilter[]).map((value) => (
          <Button
            key={value}
            size="sm"
            variant={filter === value ? "default" : "outline"}
            onClick={() => setFilter(value)}
          >
            {value === "all" ? "All" : value === "open" ? "Open" : "Closed"}
          </Button>
        ))}
      </div>
      {error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : null}
      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(280px,1fr)_minmax(0,2fr)]">
        <div className="min-h-0 overflow-auto rounded-xl border bg-card">
          <ul className="divide-y">
            {filteredRows.map((row) => (
              <li key={row.id}>
                <button
                  type="button"
                  className="flex w-full flex-col gap-1 px-4 py-3 text-left hover:bg-muted/50"
                  onClick={() => setSelected(row)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs uppercase text-muted-foreground">{row.symbol}</span>
                    <span className="rounded-full border px-2 py-0.5 text-[10px] uppercase">
                      {statusLabel(row.status)}
                    </span>
                  </div>
                  <span className="font-medium uppercase">{row.direction}</span>
                  <span className="text-sm text-muted-foreground line-clamp-2">{row.summary}</span>
                  {row.paperAction ? (
                    <span className="text-xs text-muted-foreground">
                      Paper: {row.paperAction}
                    </span>
                  ) : null}
                </button>
              </li>
            ))}
            {filteredRows.length === 0 ? (
              <li className="px-4 py-8 text-center text-sm text-muted-foreground">
                No recommendations in this view. Ask the agent to analyze gold in chat.
              </li>
            ) : null}
          </ul>
        </div>
        <div className="min-h-0 overflow-auto">
          {selected ? (
            <TradingRecommendationCard result={rowToResult(selected)} showStages={false} />
          ) : (
            <div className="flex h-full items-center justify-center rounded-xl border bg-muted/20 p-8 text-sm text-muted-foreground">
              Select a recommendation to review levels and approve/reject in paper mode.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
