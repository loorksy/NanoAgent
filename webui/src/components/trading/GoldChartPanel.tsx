import { useCallback, useEffect, useState } from "react";
import { TvChart } from "@/components/trading/TvChart";
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

export function GoldChartPanel() {
  const { getToken } = useClient();
  const [status, setStatus] = useState<TradingStatus | null>(null);
  const [quote, setQuote] = useState<QuotePayload["quote"]>(null);
  const [error, setError] = useState<string | null>(null);

  const authHeaders = useCallback((): Record<string, string> => {
    const token = getToken();
    if (!token) return {};
    return { Authorization: `Bearer ${token}` };
  }, [getToken]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
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
          throw new Error("Failed to load trading status");
        }
        const statusPayload = await statusRes.json() as TradingStatus;
        const quotePayload = await quoteRes.json() as QuotePayload;
        if (cancelled) return;
        setStatus(statusPayload);
        setQuote(quotePayload.quote ?? null);
        setError(quotePayload.error ?? null);
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
  }, [authHeaders]);

  const mid = quote?.mid;

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Gold Chart</h1>
          <p className="text-sm text-muted-foreground">
            XAUUSD · TradingView Advanced Charts · OANDA datafeed
          </p>
        </div>
        <div className="rounded-lg border bg-card px-4 py-2 text-sm">
          <div className="font-medium">
            {mid != null ? mid.toFixed(2) : "—"}
          </div>
          <div className="text-xs text-muted-foreground">
            {status?.oanda_configured ? `OANDA ${status.oanda_env}` : "OANDA not configured"}
          </div>
        </div>
      </div>

      {error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-hidden rounded-xl border bg-card">
        <TvChart getAuthToken={getToken} />
      </div>
    </div>
  );
}
