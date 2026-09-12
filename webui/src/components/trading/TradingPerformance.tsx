import { TradingRecommendationCard } from "@/components/trading/TradingRecommendationCard";
import { useClient } from "@/providers/ClientProvider";
import { useCallback, useEffect, useState } from "react";

interface PerformancePayload {
  totalRecommendations: number;
  openRecommendations: number;
  closedRecommendations: number;
  directionBreakdown: { buy: number; sell: number; wait: number };
  paperActions: number;
  recentRecommendations: Array<Record<string, unknown>>;
}

export function TradingPerformance() {
  const { getToken } = useClient();
  const [data, setData] = useState<PerformancePayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const res = await fetch("/api/trading/performance", {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) {
      setError("Failed to load performance");
      return;
    }
    setData(await res.json() as PerformancePayload);
  }, [getToken]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 60_000);
    return () => window.clearInterval(timer);
  }, [load]);

  if (error) {
    return <div className="p-6 text-sm text-destructive">{error}</div>;
  }
  if (!data) {
    return <div className="p-6 text-sm text-muted-foreground">Loading performance…</div>;
  }

  return (
    <div className="flex h-full flex-col overflow-auto p-4 sm:p-6">
      <header className="mb-6">
        <h1 className="text-lg font-semibold">Performance</h1>
        <p className="text-sm text-muted-foreground">Gold recommendations and paper trading summary</p>
      </header>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total recommendations" value={data.totalRecommendations} />
        <StatCard label="Open" value={data.openRecommendations} />
        <StatCard label="Closed" value={data.closedRecommendations} />
        <StatCard label="Paper actions" value={data.paperActions} />
      </div>
      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        <StatCard label="Buy signals" value={data.directionBreakdown.buy} />
        <StatCard label="Sell signals" value={data.directionBreakdown.sell} />
        <StatCard label="Wait" value={data.directionBreakdown.wait} />
      </div>
      <section className="mt-8">
        <h2 className="mb-3 text-sm font-semibold">Recent recommendations</h2>
        <div className="grid gap-3 lg:grid-cols-2">
          {data.recentRecommendations.map((row) => (
            <TradingRecommendationCard
              key={String(row.id)}
              result={{
                decision: String(row.direction ?? "wait"),
                summary: String(row.summary ?? ""),
                confidence: typeof row.confidence === "number" ? row.confidence : 0,
                recommendationId: String(row.id),
                recommendation: {
                  entry: row.entry as number | undefined,
                  stopLoss: row.stop_loss as number | undefined,
                  targets: (row.targets as number[]) ?? [],
                },
              }}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}
