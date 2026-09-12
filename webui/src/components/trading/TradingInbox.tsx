import { TradingRecommendationCard } from "@/components/trading/TradingRecommendationCard";
import { Button } from "@/components/ui/button";
import type { TradingResultWire } from "@/lib/trading/types";
import { useClient } from "@/providers/ClientProvider";
import { useCallback, useEffect, useState } from "react";

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
}

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

export function TradingInbox() {
  const { getToken } = useClient();
  const [rows, setRows] = useState<InboxRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<InboxRow | null>(null);

  const refresh = useCallback(async () => {
    const token = getToken();
    const res = await fetch("/api/trading/recommendations", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      setError("Failed to load recommendations");
      return;
    }
    const payload = await res.json() as { recommendations: InboxRow[] };
    setRows(payload.recommendations ?? []);
    setError(null);
  }, [getToken]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 p-4 sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Recommendations</h1>
          <p className="text-sm text-muted-foreground">
            Stored gold recommendations from agent analysis runs
          </p>
        </div>
        <Button variant="outline" onClick={() => void refresh()}>Refresh</Button>
      </div>
      {error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : null}
      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(280px,1fr)_minmax(0,2fr)]">
        <div className="min-h-0 overflow-auto rounded-xl border bg-card">
          <ul className="divide-y">
            {rows.map((row) => (
              <li key={row.id}>
                <button
                  type="button"
                  className="flex w-full flex-col gap-1 px-4 py-3 text-left hover:bg-muted/50"
                  onClick={() => setSelected(row)}
                >
                  <span className="text-xs uppercase text-muted-foreground">{row.symbol}</span>
                  <span className="font-medium uppercase">{row.direction}</span>
                  <span className="text-sm text-muted-foreground line-clamp-2">{row.summary}</span>
                </button>
              </li>
            ))}
            {rows.length === 0 ? (
              <li className="px-4 py-8 text-center text-sm text-muted-foreground">
                No recommendations yet. Ask the agent to analyze gold in chat.
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
