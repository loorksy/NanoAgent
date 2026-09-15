import { APP_WAKE_EVENT, startAppWakeBridge } from "@/lib/chart/appWake";
import { isChartPollingPaused } from "@/lib/chart/chartPolling";
import { subscribeTradingTicks } from "@/lib/trading/tickBus";
import type {
  Bar,
  DatafeedConfiguration,
  HistoryCallback,
  IBasicDataFeed,
  LibrarySymbolInfo,
  PeriodParams,
  ResolutionString,
  ResolveCallback,
  SearchSymbolResultItem,
  SubscribeBarsCallback,
} from "../../../../vendor/tradingview/charting_library/charting_library";

const DATA_SYMBOL = "XAUUSD";

export const TICK_STALE_MS = 12_000;
export const BACKFILL_AFTER_MS = 30_000;

const RES_TO_INTERVAL: Record<string, string> = {
  "1": "1m",
  "5": "5m",
  "15": "15m",
  "30": "30m",
  "60": "1h",
  "240": "4h",
  "1D": "1d",
  D: "1d",
  "1W": "1w",
  W: "1w",
};

const SUPPORTED_RESOLUTIONS = [
  "1",
  "5",
  "15",
  "30",
  "60",
  "240",
  "1D",
  "1W",
] as ResolutionString[];

const INTERVAL_MS: Record<string, number> = {
  "1m": 60_000,
  "5m": 300_000,
  "15m": 900_000,
  "30m": 1_800_000,
  "1h": 3_600_000,
  "4h": 14_400_000,
  "1d": 86_400_000,
  "1w": 604_800_000,
};

interface RawCandle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export function barEmittable(
  lastBarTimeMs: number | undefined,
  nextBarTimeMs: number,
): boolean {
  if (!Number.isFinite(nextBarTimeMs)) return false;
  if (lastBarTimeMs == null || !Number.isFinite(lastBarTimeMs)) return true;
  return nextBarTimeMs >= lastBarTimeMs;
}

function resolutionToInterval(res: string): string {
  return RES_TO_INTERVAL[res] ?? "15m";
}

function barDurationMs(interval: string): number {
  return INTERVAL_MS[interval] ?? 60_000;
}

function pollMsForResolution(res: string): number {
  const iv = resolutionToInterval(res);
  if (iv === "1m") return 1_000;
  if (iv === "5m") return 2_000;
  if (iv === "15m" || iv === "30m") return 5_000;
  if (iv === "1h") return 10_000;
  return 30_000;
}

export function buildKlinesUrl(params: {
  symbol: string;
  interval: string;
  limit?: number;
  from?: number;
  to?: number;
  before?: number;
  fresh?: boolean;
}): string {
  const search = new URLSearchParams({
    symbol: params.symbol,
    interval: params.interval,
  });
  if (params.limit != null) search.set("limit", String(params.limit));
  if (params.from != null) search.set("from", String(params.from));
  if (params.to != null) search.set("to", String(params.to));
  if (params.before != null) search.set("before", String(params.before));
  if (params.fresh) search.set("fresh", "1");
  return `/api/trading/klines?${search.toString()}`;
}

export interface TvDatafeedOptions {
  getAuthToken?: () => string;
  onBarsStale?: () => void;
}

type BarSubscription = {
  timer?: ReturnType<typeof setInterval>;
  unsubscribeTicks?: () => void;
  onVisibility?: () => void;
  onWake?: () => void;
};

function defer<T extends (...args: never[]) => void>(callback: T): T {
  return ((...args: never[]) => {
    setTimeout(() => callback(...args), 0);
  }) as T;
}

export function createTradingDatafeed(options: TvDatafeedOptions = {}): IBasicDataFeed {
  const subscriptions = new Map<string, BarSubscription>();
  const getAuthTokenRef = { current: options.getAuthToken };
  getAuthTokenRef.current = options.getAuthToken;
  let wakeDisposer: (() => void) | null = null;

  async function fetchKlines(url: string): Promise<RawCandle[]> {
    const headers: Record<string, string> = {};
    const token = getAuthTokenRef.current?.();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(url, { credentials: "same-origin", headers });
    if (!res.ok) throw new Error(`klines HTTP ${res.status}`);
    const payload = await res.json() as { candles?: RawCandle[] };
    return payload.candles ?? [];
  }

  return {
    onReady(callback: (config: DatafeedConfiguration) => void): void {
      defer(callback)({
        supported_resolutions: SUPPORTED_RESOLUTIONS,
        supports_marks: false,
        supports_timescale_marks: false,
        supports_time: true,
      });
    },

    searchSymbols(
      _userInput: string,
      _exchange: string,
      _symbolType: string,
      onResult: (items: SearchSymbolResultItem[]) => void,
    ): void {
      defer(onResult)([
        {
          symbol: DATA_SYMBOL,
          description: "Gold / US Dollar",
          exchange: "OANDA",
          ticker: DATA_SYMBOL,
          type: "forex",
        },
      ]);
    },

    resolveSymbol(
      symbolName: string,
      onResolve: ResolveCallback,
      onError: (reason: string) => void,
    ): void {
      const symbol = symbolName.toUpperCase().includes("XAU") ? DATA_SYMBOL : symbolName;
      if (symbol !== DATA_SYMBOL) {
        defer(onError)("Only XAUUSD is supported");
        return;
      }
      const info: LibrarySymbolInfo = {
        name: DATA_SYMBOL,
        ticker: DATA_SYMBOL,
        description: "Gold / US Dollar",
        type: "forex",
        session: "24x7",
        timezone: "Etc/UTC",
        exchange: "OANDA",
        listed_exchange: "OANDA",
        format: "price",
        pricescale: 100,
        minmov: 1,
        has_intraday: true,
        has_daily: true,
        has_weekly_and_monthly: true,
        supported_resolutions: SUPPORTED_RESOLUTIONS,
        volume_precision: 0,
        data_status: "streaming",
      };
      defer(onResolve)(info);
    },

    getBars(
      symbolInfo: LibrarySymbolInfo,
      resolution: ResolutionString,
      periodParams: PeriodParams,
      onResult: HistoryCallback,
      onError: (reason: string) => void,
    ): void {
      const interval = resolutionToInterval(resolution);
      const countBack = Math.min(Math.max(periodParams.countBack, 10), 4000);
      const url = buildKlinesUrl({
        symbol: symbolInfo.ticker ?? DATA_SYMBOL,
        interval,
        limit: countBack,
        from: periodParams.from ? periodParams.from * 1000 : undefined,
        to: periodParams.to ? periodParams.to * 1000 : undefined,
      });
      fetchKlines(url)
        .then((candles) => {
          const bars: Bar[] = candles
            .filter((c) => Number.isFinite(c.time) && c.time > 0)
            .map((c) => ({
              time: c.time * 1000,
              open: c.open,
              high: c.high,
              low: c.low,
              close: c.close,
              volume: c.volume,
            }))
            .sort((a, b) => a.time - b.time);
          defer(onResult)(bars, { noData: bars.length === 0 });
        })
        .catch((err: Error) => defer(onError)(err.message));
    },

    subscribeBars(
      symbolInfo: LibrarySymbolInfo,
      resolution: ResolutionString,
      onTick: SubscribeBarsCallback,
      listenerGuid: string,
      onResetCacheNeeded?: () => void,
    ): void {
      if (!wakeDisposer) wakeDisposer = startAppWakeBridge();

      const interval = resolutionToInterval(resolution);
      const ticker = symbolInfo.ticker ?? DATA_SYMBOL;
      const barMs = barDurationMs(interval);
      let forming: Bar | null = null;
      let streamAlive = false;
      let lastTickAt = 0;
      let lastEmitAt = 0;
      const subscribedAt = Date.now();

      const emit = (bar: Bar) => {
        forming = bar;
        lastEmitAt = Date.now();
        onTick(bar);
      };

      const poll = async () => {
        if (isChartPollingPaused()) return;
        const stale = lastTickAt === 0 || Date.now() - lastTickAt > TICK_STALE_MS;
        if (streamAlive && !stale) return;
        try {
          const url = buildKlinesUrl({
            symbol: ticker,
            interval,
            limit: 2,
            fresh: true,
          });
          const candles = await fetchKlines(url);
          const latest = candles[candles.length - 1];
          if (
            latest
            && Number.isFinite(latest.time)
            && barEmittable(forming?.time, latest.time * 1000)
          ) {
            emit({
              time: latest.time * 1000,
              open: latest.open,
              high: latest.high,
              low: latest.low,
              close: latest.close,
              volume: latest.volume ?? 0,
            });
          }
        } catch {
          // best-effort
        }
      };

      const applyTickPrice = (price: number, timeMs: number) => {
        const openTime = Math.floor(timeMs / barMs) * barMs;
        if (!barEmittable(forming?.time, openTime)) return;
        if (!forming || forming.time !== openTime) {
          emit({
            time: openTime,
            open: price,
            high: price,
            low: price,
            close: price,
            volume: 0,
          });
          return;
        }
        emit({
          time: openTime,
          open: forming.open,
          high: Math.max(forming.high, price),
          low: Math.min(forming.low, price),
          close: price,
          volume: forming.volume ?? 0,
        });
      };

      const sub: BarSubscription = {
        timer: setInterval(() => void poll(), pollMsForResolution(resolution)),
        unsubscribeTicks: subscribeTradingTicks((tick) => {
          if (tick.symbol !== ticker) return;
          streamAlive = true;
          lastTickAt = Date.now();
          applyTickPrice(tick.mid, tick.time || Date.now());
        }),
      };

      let lastWakeHandledAt = 0;
      const onWake = () => {
        if (typeof document !== "undefined" && document.visibilityState === "hidden") return;
        const now = Date.now();
        if (now - lastWakeHandledAt < 1_000) return;
        lastWakeHandledAt = now;
        const missedBars =
          now - (lastEmitAt > 0 ? lastEmitAt : subscribedAt) > BACKFILL_AFTER_MS;
        streamAlive = false;
        if (missedBars) {
          forming = null;
          try {
            onResetCacheNeeded?.();
          } catch {
            /* TV mid-teardown */
          }
          options.onBarsStale?.();
        }
        void poll();
      };

      const onVisibility = () => {
        if (document.visibilityState === "hidden") {
          streamAlive = false;
          return;
        }
        onWake();
      };

      sub.onWake = onWake;
      sub.onVisibility = onVisibility;
      window.addEventListener(APP_WAKE_EVENT, onWake);
      document.addEventListener("visibilitychange", onVisibility);

      subscriptions.set(listenerGuid, sub);
      void poll();
    },

    unsubscribeBars(listenerGuid: string): void {
      const sub = subscriptions.get(listenerGuid);
      if (!sub) return;
      if (sub.timer) clearInterval(sub.timer);
      sub.unsubscribeTicks?.();
      if (sub.onWake) window.removeEventListener(APP_WAKE_EVENT, sub.onWake);
      if (sub.onVisibility) {
        document.removeEventListener("visibilitychange", sub.onVisibility);
      }
      subscriptions.delete(listenerGuid);
    },
  };
}
