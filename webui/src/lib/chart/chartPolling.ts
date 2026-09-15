let chartPollingPaused = false;

export function setChartPollingPaused(paused: boolean): void {
  chartPollingPaused = paused;
}

export function isChartPollingPaused(): boolean {
  if (chartPollingPaused) return true;
  if (typeof document !== "undefined" && document.hidden) return true;
  return false;
}
