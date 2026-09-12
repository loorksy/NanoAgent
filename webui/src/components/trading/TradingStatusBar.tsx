import { useClient } from "@/providers/ClientProvider";
import { useCallback, useEffect, useState } from "react";

interface Briefing {
  summary: string;
  quote?: { mid?: number | null };
  openRecommendation?: { direction?: string; summary?: string } | null;
}

export function TradingStatusBar() {
  const { getToken } = useClient();
  const [briefing, setBriefing] = useState<Briefing | null>(null);

  const refresh = useCallback(async () => {
    const token = getToken();
    const res = await fetch("/api/trading/briefing", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) return;
    setBriefing(await res.json() as Briefing);
  }, [getToken]);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 30_000);
    return () => clearInterval(timer);
  }, [refresh]);

  if (!briefing) return null;

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-muted/30 px-3 py-2 text-xs">
      <span className="font-medium">{briefing.summary}</span>
      {briefing.openRecommendation ? (
        <span className="text-muted-foreground">
          Open {String(briefing.openRecommendation.direction ?? "").toUpperCase()} — {briefing.openRecommendation.summary}
        </span>
      ) : null}
    </div>
  );
}
