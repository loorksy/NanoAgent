import { captureTradingViewFrames } from "@/lib/trading/chartCapture";
import { ChartHostWsClient } from "@/lib/trading/chartHostWs";
import type { IChartingLibraryWidget } from "../../../vendor/tradingview/charting_library/charting_library";
import { useEffect, useRef } from "react";

interface ChartHostAgentProps {
  token: string;
  widget: IChartingLibraryWidget | null;
}

interface HostCaptureJob {
  captureId: string;
  interval?: string;
  timeframes: string[];
}

const POLL_MS = 1_500;

export function ChartHostAgent({ token, widget }: ChartHostAgentProps) {
  const busyRef = useRef(false);
  const wsRef = useRef<ChartHostWsClient | null>(null);
  const widgetRef = useRef<IChartingLibraryWidget | null>(widget);

  useEffect(() => {
    widgetRef.current = widget;
  }, [widget]);

  useEffect(() => {
    if (!token) return;
    wsRef.current = new ChartHostWsClient(token);
    let cancelled = false;

    const poll = async () => {
      while (!cancelled) {
        if (busyRef.current) {
          await new Promise((resolve) => window.setTimeout(resolve, POLL_MS));
          continue;
        }
        try {
          const res = await fetch("/api/trading/chart-host/poll", {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (!res.ok) {
            await new Promise((resolve) => window.setTimeout(resolve, POLL_MS));
            continue;
          }
          const payload = await res.json() as { job?: HostCaptureJob | null };
          const job = payload.job;
          if (!job?.captureId || !Array.isArray(job.timeframes)) {
            await new Promise((resolve) => window.setTimeout(resolve, POLL_MS));
            continue;
          }
          busyRef.current = true;
          try {
            let readyWidget = widgetRef.current;
            for (let i = 0; i < 120 && !readyWidget; i += 1) {
              await new Promise((resolve) => window.setTimeout(resolve, 500));
              readyWidget = widgetRef.current;
            }
            if (!readyWidget) {
              throw new Error("chart-host widget not ready");
            }
            for (let i = 0; i < 60; i += 1) {
              try {
                readyWidget.activeChart();
                break;
              } catch {
                await new Promise((resolve) => window.setTimeout(resolve, 500));
              }
            }
            const frames = await captureTradingViewFrames(readyWidget, job.timeframes);
            if (!frames.length) {
              throw new Error("chart-host capture returned no frames");
            }
            const client = wsRef.current ?? new ChartHostWsClient(token);
            wsRef.current = client;
            await client.submitCapture(job.captureId, frames);
          } finally {
            busyRef.current = false;
          }
        } catch (error) {
          console.error("chart-host capture failed", error);
          await new Promise((resolve) => window.setTimeout(resolve, POLL_MS));
        }
      }
    };

    void poll();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return null;
}
