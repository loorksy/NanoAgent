import { useClient } from "@/providers/ClientProvider";
import { useEffect, useRef, useState } from "react";

export interface LiveQuote {
  symbol: string;
  bid: number;
  ask: number;
  mid: number;
  ts: number;
}

export function useQuoteStream(symbol = "XAUUSD", enabled = true): LiveQuote | null {
  const { getToken } = useClient();
  const [quote, setQuote] = useState<LiveQuote | null>(null);
  const lastRenderRef = useRef(0);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    const tick = async () => {
      if (cancelled || document.hidden) return;
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
        const now = performance.now();
        if (now - lastRenderRef.current < 450) return;
        lastRenderRef.current = now;
        const mid = Number(payload.mid ?? 0);
        if (!mid) return;
        setQuote({
          symbol,
          bid: Number(payload.bid ?? mid),
          ask: Number(payload.ask ?? mid),
          mid,
          ts: Date.now(),
        });
      } catch {
        // best-effort
      }
    };
    const timer = window.setInterval(() => void tick(), 2_000);
    void tick();
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [enabled, getToken, symbol]);

  return quote;
}
