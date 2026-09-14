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
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useImperativeHandle(ref, () => ({
    currentSymbol: () => symbol,
  }), [symbol]);

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

        widgetRef.current?.remove();
        widgetRef.current = null;

        const options: ChartingLibraryWidgetOptions = {
          symbol,
          interval: (INTERVAL_TO_RES[interval] ?? "15") as ResolutionString,
          container,
          library_path: LIBRARY_PATH,
          locale: "en",
          autosize: true,
          theme: "dark",
          disabled_features: tvDisabledFeatures(variant),
          enabled_features: variant === "minimal" ? [] : ["study_templates"],
          datafeed: createTradingDatafeed({ getAuthToken }),
        };
        const widget = new Widget(options);
        widgetRef.current = widget;
        widget.onChartReady(() => {
          if (!cancelled) onWidgetReady?.(widget);
        });
        setLoading(false);
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
      widgetRef.current?.remove();
      widgetRef.current = null;
    };
  }, [getAuthToken, interval, onWidgetReady, symbol, variant]);

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
