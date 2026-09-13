import { ChartTradeOverlay } from "@/components/trading/ChartTradeOverlay";
import { TradingTeamPanel } from "@/components/trading/TradingTeamPanel";
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
}

export function TradingChartSidecar({ chatId }: TradingChartSidecarProps) {
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
    if (!capture || !widgetRef.current) return;
    if (captureRef.current === capture.captureId) return;
    captureRef.current = capture.captureId;

    void (async () => {
      try {
        const frames = await captureTradingViewFrames(
          widgetRef.current!,
          capture.timeframes,
        );
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
    })();
  }, [chatId, client, session.chartCapture]);

  return (
    <div className="flex h-full min-h-0 flex-col bg-background">
      <div className="border-b px-4 py-3">
        <h2 className="text-sm font-semibold">Gold chart</h2>
        <p className="text-xs text-muted-foreground">XAUUSD · live market · agent analysis</p>
      </div>
      {session.teamAgents.length > 0 ? (
        <div className="border-b p-3">
          <TradingTeamPanel
            agents={session.teamAgents}
            teamMode={session.result?.teamMode}
            compact
          />
        </div>
      ) : null}
      <div className="relative min-h-0 flex-1">
        <TvChart
          ref={chartRef}
          interval={session.interval}
          getAuthToken={getToken}
          onWidgetReady={(widget) => {
            widgetRef.current = widget;
          }}
        />
        <ChartTradeOverlay recommendation={session.result?.recommendation ?? null} />
      </div>
    </div>
  );
}
