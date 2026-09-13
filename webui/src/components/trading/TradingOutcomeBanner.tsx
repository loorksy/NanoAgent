import type { TradingOutcomeWire } from "@/lib/trading/types";
import { Button } from "@/components/ui/button";

interface TradingOutcomeBannerProps {
  alerts: TradingOutcomeWire[];
  onDismiss: (id: string) => void;
}

export function TradingOutcomeBanner({ alerts, onDismiss }: TradingOutcomeBannerProps) {
  if (alerts.length === 0) return null;
  return (
    <div className="space-y-2">
      {alerts.map((alert) => (
        <div
          key={`${alert.recommendationId}-${alert.outcomeStatus}`}
          className="flex items-start justify-between gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm"
        >
          <div>
            <p className="font-medium uppercase tracking-wide text-amber-900 dark:text-amber-100">
              {alert.direction} · {alert.outcomeStatus}
            </p>
            <p className="mt-1 whitespace-pre-wrap text-muted-foreground">{alert.summary}</p>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onDismiss(`${alert.recommendationId}-${alert.outcomeStatus}`)}
          >
            Dismiss
          </Button>
        </div>
      ))}
    </div>
  );
}
