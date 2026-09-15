import { ChartHostAgent } from "@/components/trading/ChartHostAgent";
import { TvChart } from "@/components/trading/TvChart";
import { useMemo, useState } from "react";
import type { IChartingLibraryWidget } from "../../vendor/tradingview/charting_library/charting_library";

function readHostToken(): string {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams(window.location.search);
  return params.get("token")?.trim() ?? "";
}

export default function ChartHostPage() {
  const token = useMemo(() => readHostToken(), []);
  const [widget, setWidget] = useState<IChartingLibraryWidget | null>(null);
  const getAuthToken = useMemo(() => () => token, [token]);

  if (!token) {
    return (
      <div className="flex h-full items-center justify-center bg-[#0b0f14] text-sm text-white/70">
        Chart host token missing
      </div>
    );
  }

  return (
    <div className="h-full min-h-screen w-full bg-[#0b0f14]">
      <TvChart
        interval="15m"
        variant="minimal"
        className="min-h-screen"
        getAuthToken={getAuthToken}
        onWidgetReady={setWidget}
      />
      <ChartHostAgent token={token} widget={widget} />
    </div>
  );
}
