interface TradeRecommendation {
  action?: string;
  entry?: number | null;
  stopLoss?: number | null;
  targets?: number[];
}

interface ChartTradeOverlayProps {
  recommendation?: TradeRecommendation | null;
}

export function ChartTradeOverlay({ recommendation }: ChartTradeOverlayProps) {
  if (!recommendation || recommendation.action === "wait") {
    return null;
  }

  const { entry, stopLoss, targets = [] } = recommendation;

  return (
    <div className="absolute bottom-4 left-4 z-10 rounded-lg border bg-background/90 p-3 text-xs shadow-md backdrop-blur">
      <div className="font-semibold uppercase">{recommendation.action}</div>
      {entry != null ? <div>Entry: {entry.toFixed(2)}</div> : null}
      {stopLoss != null ? <div>SL: {stopLoss.toFixed(2)}</div> : null}
      {targets.length > 0 ? (
        <div>TP: {targets.map((t) => t.toFixed(2)).join(" / ")}</div>
      ) : null}
    </div>
  );
}
