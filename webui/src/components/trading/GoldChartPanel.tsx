import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { AgentCards, type AgentCard } from "@/components/trading/AgentCards";
import { ChartTradeOverlay } from "@/components/trading/ChartTradeOverlay";
import { TradingStatusBar } from "@/components/trading/TradingStatusBar";
import { TvChart } from "@/components/trading/TvChart";
import { setChartPollingPaused } from "@/lib/chart/chartPolling";
import { applyTradingDrawings } from "@/lib/chart/tv/tvDrawingAdapter";
import { useActiveRecommendation } from "@/lib/trading/activeRecommendationStore";
import { Button } from "@/components/ui/button";
import { useClient } from "@/providers/ClientProvider";
import { fetchWithTimeout } from "@/lib/http";

interface TradingStatus {
  symbol: string;
  oanda_configured: boolean;
  oanda_env: string;
  runtime: {
    paused: boolean;
    kill_switch: boolean;
    paper_mode: boolean;
  };
}

interface QuotePayload {
  quote?: {
    bid: number | null;
    ask: number | null;
    mid: number | null;
    tradeable: boolean;
  } | null;
  error?: string;
}

interface AnalysisResult {
  decision: string;
  summary: string;
  confidence: number;
  locale?: string;
  cards: AgentCard[];
  recommendation?: {
    action?: string;
    entry?: number;
    stopLoss?: number;
    targets?: number[];
  };
  recommendationId?: string;
  drawings?: Array<Record<string, unknown>>;
}

export function GoldChartPanel() {
  const { t, i18n } = useTranslation();
  const { getToken } = useClient();
  const [status, setStatus] = useState<TradingStatus | null>(null);
  const [quote, setQuote] = useState<QuotePayload["quote"]>(null);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const chartWidgetRef = useRef<import("../../../vendor/tradingview/charting_library/charting_library").IChartingLibraryWidget | null>(null);
  const activeRecommendation = useActiveRecommendation();

  useEffect(() => {
    setChartPollingPaused(false);
    return () => setChartPollingPaused(true);
  }, []);

  useEffect(() => {
    if (analysis?.drawings?.length) return;
    const lines = activeRecommendation.lines;
    if (!lines.length) return;
    void applyTradingDrawings(
      chartWidgetRef.current,
      lines.map((line) => ({
        type: line.kind === "entry" ? "entry" : line.kind === "sl" ? "stop" : "target",
        label: line.label ?? line.kind,
        color: line.kind === "entry" ? "#3b82f6" : line.kind === "sl" ? "#ef4444" : "#22c55e",
        points: [{ price: line.price }],
      })),
    );
  }, [activeRecommendation.lines, analysis?.drawings]);

  const authHeaders = useCallback((): Record<string, string> => {
    const token = getToken();
    if (!token) return {};
    return { Authorization: `Bearer ${token}` };
  }, [getToken]);

  const refreshMarket = useCallback(async () => {
    const [statusRes, quoteRes] = await Promise.all([
      fetchWithTimeout("/api/trading/status", {
        credentials: "same-origin",
        headers: authHeaders(),
      }),
      fetchWithTimeout("/api/trading/quote?symbol=XAUUSD", {
        credentials: "same-origin",
        headers: authHeaders(),
      }),
    ]);
    if (!statusRes.ok || !quoteRes.ok) {
      throw new Error(t("trading.chart.loadStatusFailed"));
    }
    const statusPayload = await statusRes.json() as TradingStatus;
    const quotePayload = await quoteRes.json() as QuotePayload;
    setStatus(statusPayload);
    setQuote(quotePayload.quote ?? null);
    setError(quotePayload.error ?? null);
  }, [authHeaders, t]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        await refreshMarket();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    };
    void load();
    const timer = setInterval(() => void load(), 15_000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [refreshMarket]);

  const runAnalysis = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const res = await fetchWithTimeout(
        "/api/trading/analyze?interval=15m&team_mode=core",
        { credentials: "same-origin", headers: authHeaders() },
        120_000,
      );
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || t("trading.chart.analyzeFailed", { status: res.status }));
      }
      const payload = await res.json() as AnalysisResult;
      setAnalysis(payload);
      if (payload.drawings?.length) {
        void applyTradingDrawings(chartWidgetRef.current, payload.drawings as Array<{
          type: string;
          label: string;
          color: string;
          points: Array<{ time?: number; price?: number }>;
        }>);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setAnalyzing(false);
    }
  };

  const mid = quote?.mid;

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("trading.chart.title")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("trading.chart.subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => void runAnalysis()} disabled={analyzing}>
            {analyzing ? t("trading.chart.analyzing") : t("trading.chart.analyze")}
          </Button>
          <div className="rounded-lg border bg-card px-4 py-2 text-sm">
            <div className="font-medium">
              {mid != null ? mid.toFixed(2) : "—"}
            </div>
            <div className="text-xs text-muted-foreground">
              {status?.oanda_configured ? t("trading.chart.liveMarket") : t("trading.chart.marketUnavailable")}
            </div>
          </div>
        </div>
      </div>

      <TradingStatusBar />

      {error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {analysis ? (
        <div className="rounded-lg border bg-muted/30 p-3 text-sm">
          <div className="font-medium uppercase">{analysis.decision}</div>
          <p className="text-muted-foreground">{analysis.summary}</p>
          <p className="text-xs">
            {t("trading.chart.confidence", { percent: (analysis.confidence * 100).toFixed(0) })}
          </p>
        </div>
      ) : null}

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
        <div className="relative min-h-[420px] overflow-hidden rounded-xl border bg-card">
          <TvChart
            getAuthToken={getToken}
            onWidgetReady={(widget) => {
              chartWidgetRef.current = widget;
            }}
          />
          <ChartTradeOverlay recommendation={analysis?.recommendation ?? null} />
        </div>
        <div className="min-h-0 overflow-auto rounded-xl border bg-card p-3">
          <h2 className="mb-3 text-sm font-semibold">{t("trading.chart.recommendationCards")}</h2>
          <AgentCards
            cards={analysis?.cards ?? []}
            locale={analysis?.locale ?? i18n.resolvedLanguage}
          />
        </div>
      </div>
    </div>
  );
}
