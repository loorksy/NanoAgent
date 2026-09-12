import { TradingStatusBar } from "@/components/trading/TradingStatusBar";
import { TradingRecommendationCard } from "@/components/trading/TradingRecommendationCard";
import { useClient } from "@/providers/ClientProvider";
import { useCallback, useEffect, useState } from "react";

interface BriefingPayload {
  summary: string;
  quote: { mid?: number | null; bid?: number | null; ask?: number | null };
  openRecommendation: Record<string, unknown> | null;
  recentRecommendations: Array<Record<string, unknown>>;
}

export function TradingBriefingPanel() {
  const { getToken } = useClient();
  const [briefing, setBriefing] = useState<BriefingPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const res = await fetch("/api/trading/briefing", {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) {
      setError("Failed to load briefing");
      return;
    }
    setBriefing(await res.json() as BriefingPayload);
  }, [getToken]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 30_000);
    return () => window.clearInterval(timer);
  }, [load]);

  return (
    <div className="flex h-full flex-col overflow-auto p-4 sm:p-6">
      <header className="mb-4">
        <h1 className="text-lg font-semibold">Briefing</h1>
        <p className="text-sm text-muted-foreground">
          Live gold market snapshot and open setup. Connect Telegram or WhatsApp from
          <span className="font-medium"> Channels </span>
          in the sidebar to chat with the agent outside the browser.
        </p>
      </header>
      <TradingStatusBar />
      {error ? <p className="mt-4 text-sm text-destructive">{error}</p> : null}
      {briefing ? (
        <div className="mt-6 space-y-6">
          <div className="rounded-lg border bg-card p-4">
            <p className="text-sm font-medium">{briefing.summary}</p>
            {briefing.quote.mid != null ? (
              <p className="mt-2 text-xs text-muted-foreground">
                Bid {briefing.quote.bid ?? "—"} · Ask {briefing.quote.ask ?? "—"}
              </p>
            ) : null}
          </div>
          {briefing.openRecommendation ? (
            <section>
              <h2 className="mb-2 text-sm font-semibold">Open recommendation</h2>
              <TradingRecommendationCard
                result={{
                  decision: String(briefing.openRecommendation.direction ?? "wait"),
                  summary: String(briefing.openRecommendation.summary ?? ""),
                  confidence: typeof briefing.openRecommendation.confidence === "number"
                    ? briefing.openRecommendation.confidence
                    : 0,
                  recommendationId: String(briefing.openRecommendation.id ?? ""),
                  recommendation: {
                    entry: briefing.openRecommendation.entry as number | undefined,
                    stopLoss: briefing.openRecommendation.stop_loss as number | undefined,
                    targets: (briefing.openRecommendation.targets as number[]) ?? [],
                  },
                }}
              />
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
