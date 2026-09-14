import { ChartTradeOverlay } from "@/components/trading/ChartTradeOverlay";
import { TvChart, type TvChartHandle } from "@/components/trading/TvChart";
import { applyTradingDrawings } from "@/lib/chart/tv/tvDrawingAdapter";
import { captureTradingViewFrames } from "@/lib/trading/chartCapture";
import {
  clearChartCapture,
  getTradingSession,
  subscribeTradingSession,
} from "@/lib/trading/session-store";
import { useClient } from "@/providers/ClientProvider";
import { useEffect, useRef, useState } from "react";

interface TradingChartSidecarProps {
  chatId: string;
  /** Minimal chrome for AiChart-style split pane / bottom sheet. */
  minimal?: boolean;
}

export function TradingChartSidecar({ chatId, minimal = true }: TradingChartSidecarProps) {
  const { client, getToken } = useClient();
  const chartRef = useRef<TvChartHandle>(null);
  const widgetRef = useRef<import("../../../vendor/tradingview/charting_library/charting_library").IChartingLibraryWidget | null>(null);
  const captureRef = useRef<string | null>(null);
  const [session, setSession] = useState(() => getTradingSession(chatId));

  useEffect(() => {
    return subscribeTradingSession((id) => {
      if (id === chatId) setSession(getTradingSession(chatId));
    });
  }, [chatId]);

  useEffect(() => {
    if (!session.result?.drawings?.length) return;
    void applyTradingDrawings(
      widgetRef.current,
      session.result.drawings as Array<{
        type: string;
        label: string;
        color: string;
        points: Array<{ time?: number; price?: number }>;
      }>,
    );
  }, [session.result?.drawings]);

  useEffect(() => {
    const capture = session.chartCapture;
    if (!capture) return;
    if (captureRef.current === capture.captureId) return;

    let cancelled = false;
    let attempts = 0;

    const runCapture = async () => {
      while (!cancelled && attempts < 40) {
        const widget = widgetRef.current;
        if (!widget) {
          attempts += 1;
          await new Promise((resolve) => window.setTimeout(resolve, 250));
          continue;
        }
        captureRef.current = capture.captureId;
        try {
          const frames = await captureTradingViewFrames(widget, capture.timeframes);
          await client.requestMutation("trading.chart_capture", {
            captureId: capture.captureId,
            sessionKey: capture.sessionKey,
            frames,
          });
        } catch {
          await client.requestMutation("trading.chart_capture", {
            captureId: capture.captureId,
            sessionKey: capture.sessionKey,
            frames: [],
          }).catch(() => undefined);
        } finally {
          clearChartCapture(chatId);
        }
        return;
      }
    };

    void runCapture();
    return () => {
      cancelled = true;
    };
  }, [chatId, client, session.chartCapture]);

  return (
    <div className="flex h-full min-h-0 flex-col bg-background">
      <div className="relative min-h-0 flex-1">
        <TvChart
          ref={chartRef}
          interval={session.interval}
          variant={minimal ? "minimal" : "full"}
          getAuthToken={getToken}
          className="min-h-0"
          onWidgetReady={(widget) => {
            widgetRef.current = widget;
          }}
        />
        <ChartTradeOverlay recommendation={session.result?.recommendation ?? null} />
      </div>
    </div>
  );
}
