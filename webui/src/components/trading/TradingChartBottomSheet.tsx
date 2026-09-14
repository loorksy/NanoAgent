import { TradingChartSidecar } from "@/components/trading/TradingChartSidecar";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import {
  getTradingSession,
  setTradingChartOpen,
  subscribeTradingSession,
} from "@/lib/trading/session-store";
import { Suspense, useEffect, useState } from "react";

interface TradingChartBottomSheetProps {
  chatId: string;
}

export function TradingChartBottomSheet({ chatId }: TradingChartBottomSheetProps) {
  const [open, setOpen] = useState(() => getTradingSession(chatId).chartOpen);

  useEffect(() => {
    return subscribeTradingSession((id) => {
      if (id !== chatId) return;
      setOpen(getTradingSession(chatId).chartOpen);
    });
  }, [chatId]);

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setTradingChartOpen(chatId, false);
      }}
    >
      <SheetContent
        side="bottom"
        className="h-[min(78vh,720px)] gap-0 border-t border-border/60 p-0 lg:hidden"
        showCloseButton
      >
        <SheetTitle className="sr-only">Gold chart</SheetTitle>
        <Suspense fallback={<div className="p-4 text-sm text-muted-foreground">Loading chart…</div>}>
          <TradingChartSidecar chatId={chatId} minimal />
        </Suspense>
      </SheetContent>
    </Sheet>
  );
}
