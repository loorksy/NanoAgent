import type { IChartingLibraryWidget, ResolutionString } from "../../../vendor/tradingview/charting_library/charting_library";

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

export interface ChartCaptureFrame {
  timeframe: string;
  image?: string;
  context?: string;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function downscaleDataUrl(dataUrl: string, maxWidth = 960): Promise<string> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      const scale = Math.min(1, maxWidth / image.width);
      const width = Math.max(1, Math.round(image.width * scale));
      const height = Math.max(1, Math.round(image.height * scale));
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        resolve(dataUrl);
        return;
      }
      ctx.drawImage(image, 0, 0, width, height);
      resolve(canvas.toDataURL("image/jpeg", 0.72));
    };
    image.onerror = () => reject(new Error("Failed to decode chart snapshot"));
    image.src = dataUrl;
  });
}

export async function captureTradingViewFrames(
  widget: IChartingLibraryWidget,
  timeframes: string[],
): Promise<ChartCaptureFrame[]> {
  const chart = widget.activeChart();
  const frames: ChartCaptureFrame[] = [];
  for (const timeframe of timeframes) {
    const resolution = (INTERVAL_TO_RES[timeframe] ?? "15") as ResolutionString;
    try {
      await chart.setResolution(resolution);
      await sleep(450);
      const canvas = await widget.takeClientScreenshot({ hideResolution: false });
      const raw = canvas.toDataURL("image/png");
      const image = await downscaleDataUrl(raw);
      frames.push({
        timeframe,
        image,
        context: `TradingView snapshot at ${timeframe}`,
      });
    } catch {
      // Best-effort: skip frames that fail to render.
    }
  }
  return frames;
}
