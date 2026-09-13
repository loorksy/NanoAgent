import { TradingOutcomeBanner } from "@/components/trading/TradingOutcomeBanner";
import {
  dismissTradingOutcome,
  getTradingSession,
  subscribeTradingSession,
} from "@/lib/trading/session-store";
import { useEffect, useState } from "react";

interface TradingOutcomeStripProps {
  chatId: string;
}

export function TradingOutcomeStrip({ chatId }: TradingOutcomeStripProps) {
  const [session, setSession] = useState(() => getTradingSession(chatId));

  useEffect(() => {
    return subscribeTradingSession((id) => {
      if (id === chatId) setSession(getTradingSession(chatId));
    });
  }, [chatId]);

  if (session.outcomeAlerts.length === 0) return null;

  return (
    <div className="border-b bg-background px-4 py-2">
      <TradingOutcomeBanner
        alerts={session.outcomeAlerts}
        onDismiss={(key) => dismissTradingOutcome(chatId, key)}
      />
    </div>
  );
}
