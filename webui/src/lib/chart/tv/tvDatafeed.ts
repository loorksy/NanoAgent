import { isChartPollingPaused } from "@/lib/chart/chartPolling";
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

interface RawCandle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

function resolutionToInterval(res: string): string {
  return RES_TO_INTERVAL[res] ?? "15m";
}

function resolutionToSeconds(res: string): number {
  const iv = resolutionToInterval(res);
  const map: Record<string, number> = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
  };
  return map[iv] ?? 900;
}

function pollMsForResolution(res: string): number {
  const secs = resolutionToSeconds(res);
  if (secs <= 60) return 1_000;
  if (secs <= 300) return 3_000;
  return Math.min(Math.max(Math.floor(secs * 1000 / 6), 15_000), 60_000);
}

export function buildKlinesUrl(params: {
  symbol: string;
  interval: string;
  limit?: number;
  from?: number;
  to?: number;
  before?: number;
}): string {
  const search = new URLSearchParams({
    symbol: params.symbol,
    interval: params.interval,
  });
  if (params.limit != null) search.set("limit", String(params.limit));
  if (params.from != null) search.set("from", String(params.from));
  if (params.to != null) search.set("to", String(params.to));
  if (params.before != null) search.set("before", String(params.before));
  return `/api/trading/klines?${search.toString()}`;
}

export interface TvDatafeedOptions {
  getAuthToken?: () => string;
}

function defer<T extends (...args: never[]) => void>(callback: T): T {
  return ((...args: never[]) => {
    setTimeout(() => callback(...args), 0);
  }) as T;
}

export function createTradingDatafeed(options: TvDatafeedOptions = {}): IBasicDataFeed {
  const subscriptions = new Map<string, ReturnType<typeof setInterval>>();

  async function fetchKlines(url: string): Promise<RawCandle[]> {
    const headers: Record<string, string> = {};
    const token = options.getAuthToken?.();
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
          const bars: Bar[] = candles.map((c) => ({
            time: c.time * 1000,
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
            volume: c.volume,
          }));
          defer(onResult)(bars, { noData: bars.length === 0 });
        })
        .catch((err: Error) => defer(onError)(err.message));
    },

    subscribeBars(
      symbolInfo: LibrarySymbolInfo,
      resolution: ResolutionString,
      onTick: SubscribeBarsCallback,
      listenerGuid: string,
    ): void {
      const interval = resolutionToInterval(resolution);
      const pollMs = pollMsForResolution(resolution);
      let lastKnown: { time: number; close: number } | null = null;

      const poll = async () => {
        if (isChartPollingPaused()) return;
        try {
          const url = buildKlinesUrl({
            symbol: symbolInfo.ticker ?? DATA_SYMBOL,
            interval,
            limit: 2,
          });
          const candles = await fetchKlines(url);
          const latest = candles[candles.length - 1];
          if (!latest) return;
          const barTime = latest.time * 1000;
          if (
            lastKnown != null
            && lastKnown.time === barTime
            && lastKnown.close === latest.close
          ) {
            return;
          }
          if (lastKnown != null && barTime < lastKnown.time) return;
          lastKnown = { time: barTime, close: latest.close };
          onTick({
            time: barTime,
            open: latest.open,
            high: latest.high,
            low: latest.low,
            close: latest.close,
            volume: latest.volume,
          });
        } catch {
          // best-effort polling
        }
      };

      const timer = setInterval(() => void poll(), pollMs);
      subscriptions.set(listenerGuid, timer);
      void poll();
    },

    unsubscribeBars(listenerGuid: string): void {
      const timer = subscriptions.get(listenerGuid);
      if (timer) clearInterval(timer);
      subscriptions.delete(listenerGuid);
    },
  };
}
