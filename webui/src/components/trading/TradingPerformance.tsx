import { TradingOutcomeBanner } from "@/components/trading/TradingOutcomeBanner";
import { TradingRecommendationCard } from "@/components/trading/TradingRecommendationCard";
import type { TradingOutcomeWire } from "@/lib/trading/types";
import { useClient } from "@/providers/ClientProvider";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

interface PerformancePayload {
  totalRecommendations: number;
  openRecommendations: number;
  closedRecommendations: number;
  directionBreakdown: { buy: number; sell: number; wait: number };
  outcomeBreakdown?: Record<string, number>;
  paperActions: number;
  recentRecommendations: Array<Record<string, unknown>>;
  recentOutcomeAlerts?: TradingOutcomeWire[];
}

export function TradingPerformance() {
  const { t } = useTranslation();
  const { getToken } = useClient();
  const [data, setData] = useState<PerformancePayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(() => new Set());

  const load = useCallback(async () => {
    setError(null);
    const res = await fetch("/api/trading/performance", {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) {
      setError(t("trading.performance.loadFailed"));
      return;
    }
    setData(await res.json() as PerformancePayload);
  }, [getToken, t]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 60_000);
    return () => window.clearInterval(timer);
  }, [load]);

  if (error) {
    return <div className="p-6 text-sm text-destructive">{error}</div>;
  }
  if (!data) {
    return <div className="p-6 text-sm text-muted-foreground">{t("trading.performance.loading")}</div>;
  }

  const outcomes = data.outcomeBreakdown ?? {};
  const visibleAlerts = (data.recentOutcomeAlerts ?? []).filter(
    (alert) => !dismissedAlerts.has(`${alert.recommendationId}-${alert.outcomeStatus}`),
  );

  return (
    <div className="flex h-full flex-col overflow-auto p-4 sm:p-6">
      <header className="mb-6">
        <h1 className="text-lg font-semibold">{t("trading.performance.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("trading.performance.subtitle")}</p>
      </header>
      {visibleAlerts.length > 0 ? (
        <div className="mb-6">
          <TradingOutcomeBanner
            alerts={visibleAlerts}
            onDismiss={(key) => setDismissedAlerts((current) => new Set(current).add(key))}
          />
        </div>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label={t("trading.performance.totalRecommendations")} value={data.totalRecommendations} />
        <StatCard label={t("trading.performance.open")} value={data.openRecommendations} />
        <StatCard label={t("trading.performance.closed")} value={data.closedRecommendations} />
        <StatCard label={t("trading.performance.paperActions")} value={data.paperActions} />
      </div>
      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        <StatCard label={t("trading.performance.buySignals")} value={data.directionBreakdown.buy} />
        <StatCard label={t("trading.performance.sellSignals")} value={data.directionBreakdown.sell} />
        <StatCard label={t("trading.performance.wait")} value={data.directionBreakdown.wait} />
      </div>
      <section className="mt-6">
        <h2 className="mb-3 text-sm font-semibold">{t("trading.performance.outcomeTracking")}</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label={t("trading.performance.inTrade")} value={outcomes.in_trade ?? 0} />
          <StatCard label={t("trading.performance.waitingEntry")} value={outcomes.waiting ?? 0} />
          <StatCard label={t("trading.performance.tp1Hit")} value={outcomes.tp1 ?? 0} />
          <StatCard label={t("trading.performance.invalidated")} value={outcomes.invalidated ?? 0} />
        </div>
      </section>
      <section className="mt-8">
        <h2 className="mb-3 text-sm font-semibold">{t("trading.performance.recentRecommendations")}</h2>
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
                  executionState: typeof row.status === "string" ? row.status : undefined,
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
