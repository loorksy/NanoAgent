export const CHART_TOGGLE_EVENT = "nanobot:trading-chart-toggle";

export interface ChartToggleDetail {
  chatId: string;
  open: boolean;
}

export function dispatchChartToggle(chatId: string, open: boolean): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<ChartToggleDetail>(CHART_TOGGLE_EVENT, {
      detail: { chatId, open },
    }),
  );
}

export function subscribeChartToggle(
  listener: (detail: ChartToggleDetail) => void,
): () => void {
  if (typeof window === "undefined") return () => undefined;
  const handler = (event: Event) => {
    const custom = event as CustomEvent<ChartToggleDetail>;
    if (!custom.detail?.chatId) return;
    listener(custom.detail);
  };
  window.addEventListener(CHART_TOGGLE_EVENT, handler);
  return () => window.removeEventListener(CHART_TOGGLE_EVENT, handler);
}
