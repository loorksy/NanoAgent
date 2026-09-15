import { useClient } from "@/providers/ClientProvider";
import { useEffect, useRef, useState } from "react";

export interface LiveQuote {
  symbol: string;
  bid: number;
  ask: number;
  mid: number;
  ts: number;
}

const HTTP_FALLBACK_MS = 2_000;
const WS_STALE_MS = 4_000;

export function useQuoteStream(symbol = "XAUUSD", enabled = true): LiveQuote | null {
  const { client, getToken } = useClient();
  const [quote, setQuote] = useState<LiveQuote | null>(null);
  const lastRenderRef = useRef(0);
  const lastWsRef = useRef(0);

  useEffect(() => {
    if (!enabled) return;
    const applyQuote = (mid: number, bid: number, ask: number, ts: number) => {
      const now = performance.now();
      if (now - lastRenderRef.current < 200) return;
      lastRenderRef.current = now;
      setQuote({ symbol, bid, ask, mid, ts });
    };

    const unsubscribe = client.onTradingStream((event) => {
      if (event.kind !== "quote" || event.symbol !== symbol) return;
      const mid = Number(event.mid);
      if (!mid) return;
      lastWsRef.current = Date.now();
      applyQuote(
        mid,
        Number(event.bid ?? mid),
        Number(event.ask ?? mid),
        event.ts || Date.now(),
      );
    });

    let cancelled = false;
    const tick = async () => {
      if (cancelled || document.hidden) return;
      if (Date.now() - lastWsRef.current < WS_STALE_MS) return;
      try {
        const token = getToken();
        const res = await fetch(
          `/api/trading/quote?symbol=${encodeURIComponent(symbol)}`,
          { headers: token ? { Authorization: `Bearer ${token}` } : {} },
        );
        if (!res.ok) return;
        const payload = await res.json() as {
          bid?: number;
          ask?: number;
          mid?: number;
        };
        const mid = Number(payload.mid ?? 0);
        if (!mid) return;
        applyQuote(mid, Number(payload.bid ?? mid), Number(payload.ask ?? mid), Date.now());
      } catch {
        // best-effort
      }
    };
    const timer = window.setInterval(() => void tick(), HTTP_FALLBACK_MS);
    void tick();
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      unsubscribe();
    };
  }, [client, enabled, getToken, symbol]);

  return quote;
}
