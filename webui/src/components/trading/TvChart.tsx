import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import type {
  ChartingLibraryWidgetConstructor,
  ChartingLibraryWidgetOptions,
  IChartingLibraryWidget,
  ResolutionString,
} from "../../../vendor/tradingview/charting_library/charting_library";
import { acquireChartPolling } from "@/lib/chart/chartPolling";
import { createTradingDatafeed } from "@/lib/chart/tv/tvDatafeed";
import {
  tvDisabledFeatures,
  type TvChartVariant,
} from "@/lib/chart/tv/tvWidgetConfig";
import { cn } from "@/lib/utils";

declare global {
  interface Window {
    TradingView?: { widget: ChartingLibraryWidgetConstructor };
  }
}

const DATA_SYMBOL = "XAUUSD";
const LIBRARY_PATH = "/charting_library/";
const SCRIPT_SRC = "/charting_library/charting_library.standalone.js";

const INTERVAL_TO_RES: Record<string, string> = {
  "1m": "1",
  "5m": "5",
  "15m": "15",
  "30m": "30",
  "1h": "60",
  "4h": "240",
  "1d": "1D",
  "1w": "1W",
};

let scriptPromise: Promise<void> | null = null;

function loadTvScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.TradingView?.widget) return Promise.resolve();
  if (scriptPromise) return scriptPromise;
  scriptPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${SCRIPT_SRC}"]`,
    );
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("tv load")));
      if (window.TradingView?.widget) resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("tv load"));
    document.head.appendChild(script);
  });
  return scriptPromise;
}

export type TvChartHandle = {
  currentSymbol: () => string;
  reload: () => void;
};

export interface TvChartProps {
  symbol?: string;
  interval?: string;
  className?: string;
  variant?: TvChartVariant;
  getAuthToken?: () => string;
  onWidgetReady?: (widget: IChartingLibraryWidget) => void;
}

export const TvChart = forwardRef<TvChartHandle, TvChartProps>(function TvChart(
  {
    symbol = DATA_SYMBOL,
    interval = "15m",
    className,
    variant = "full",
    getAuthToken,
    onWidgetReady,
  },
  ref,
) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const widgetRef = useRef<IChartingLibraryWidget | null>(null);
  const readyRef = useRef(false);
  const lastBarsResetRef = useRef(0);
  const getAuthTokenRef = useRef(getAuthToken);
  const onWidgetReadyRef = useRef(onWidgetReady);
  const symbolRef = useRef(symbol);
  const intervalRef = useRef(interval);
  const variantRef = useRef(variant);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  getAuthTokenRef.current = getAuthToken;
  onWidgetReadyRef.current = onWidgetReady;
  symbolRef.current = symbol;
  intervalRef.current = interval;
  variantRef.current = variant;

  useImperativeHandle(ref, () => ({
    currentSymbol: () => symbolRef.current,
    reload: () => {
      if (!readyRef.current) return;
      try {
        widgetRef.current?.activeChart().resetData();
      } catch {
        /* widget torn down */
      }
    },
  }), []);

  useEffect(() => {
    return acquireChartPolling();
  }, []);

  // Mount widget once — symbol/interval sync via setSymbol/setResolution.
  useEffect(() => {
    let cancelled = false;
    const container = containerRef.current;
    if (!container) return () => undefined;

    setLoading(true);
    setError(null);

    void loadTvScript()
      .then(() => {
        if (cancelled || !container) return;
        const Widget = window.TradingView?.widget;
        if (!Widget) throw new Error("TradingView widget unavailable");

        const options: ChartingLibraryWidgetOptions = {
          symbol: symbolRef.current,
          interval: (INTERVAL_TO_RES[intervalRef.current] ?? "15") as ResolutionString,
          container,
          library_path: LIBRARY_PATH,
          locale: "en",
          autosize: true,
          theme: "dark",
          disabled_features: tvDisabledFeatures(variantRef.current),
          enabled_features: variantRef.current === "minimal" ? [] : ["study_templates"],
          datafeed: createTradingDatafeed({
            getAuthToken: () => getAuthTokenRef.current?.() ?? "",
            onBarsStale: () => {
              if (!readyRef.current) return;
              const now = Date.now();
              if (now - lastBarsResetRef.current < 2_000) return;
              lastBarsResetRef.current = now;
              try {
                widgetRef.current?.activeChart().resetData();
              } catch {
                /* ignore */
              }
            },
          }),
        };
        const widget = new Widget(options);
        widgetRef.current = widget;
        widget.onChartReady(() => {
          if (cancelled) return;
          readyRef.current = true;
          setLoading(false);
          onWidgetReadyRef.current?.(widget);
        });
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
      readyRef.current = false;
      widgetRef.current?.remove();
      widgetRef.current = null;
    };
  }, []);

  useEffect(() => {
    const widget = widgetRef.current;
    if (!widget || !readyRef.current) return;
    try {
      const chart = widget.activeChart();
      const current = chart.symbol();
      const bare = current.includes(":") ? current.split(":").pop()! : current;
      if (bare !== symbol) {
        chart.setSymbol(symbol, () => undefined);
      }
    } catch {
      /* chart not ready */
    }
  }, [symbol]);

  useEffect(() => {
    const widget = widgetRef.current;
    if (!widget || !readyRef.current) return;
    try {
      const chart = widget.activeChart();
      const target = (INTERVAL_TO_RES[interval] ?? "15") as ResolutionString;
      if (chart.resolution() !== target) {
        chart.setResolution(target, () => undefined);
      }
    } catch {
      /* chart not ready */
    }
  }, [interval]);

  return (
    <div
      className={cn(
        "relative h-full min-h-[420px] w-full",
        variant === "minimal" && "aichart-minimal-chart",
        className,
      )}
    >
      {loading ? (
        <div className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
          Loading chart…
        </div>
      ) : null}
      {error ? (
        <div className="absolute inset-0 flex items-center justify-center px-6 text-center text-sm text-destructive">
          {error}
        </div>
      ) : null}
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
});
