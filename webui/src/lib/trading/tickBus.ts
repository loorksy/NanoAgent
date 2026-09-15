export interface TradingTick {
  symbol: string;
  bid: number;
  ask: number;
  mid: number;
  time: number;
}

const listeners = new Set<(tick: TradingTick) => void>();

export function publishTradingTick(tick: TradingTick): void {
  for (const listener of listeners) {
    try {
      listener(tick);
    } catch {
      // one bad subscriber must not stall the bus
    }
  }
}

export function subscribeTradingTicks(
  listener: (tick: TradingTick) => void,
): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
