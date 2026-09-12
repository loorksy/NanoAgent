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
      callback({
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
      onResult([
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
        onError("Only XAUUSD is supported");
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
      onResolve(info);
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
          onResult(bars, { noData: bars.length === 0 });
        })
        .catch((err: Error) => onError(err.message));
    },

    subscribeBars(
      symbolInfo: LibrarySymbolInfo,
      resolution: ResolutionString,
      onTick: SubscribeBarsCallback,
      listenerGuid: string,
    ): void {
      const interval = resolutionToInterval(resolution);
      const pollMs = pollMsForResolution(resolution);
      let lastBarTime: number | undefined;

      const poll = async () => {
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
          if (lastBarTime != null && barTime < lastBarTime) return;
          lastBarTime = barTime;
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
