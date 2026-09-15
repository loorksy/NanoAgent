let pauseDepth = 0;

export function acquireChartPolling(): () => void {
  pauseDepth += 1;
  return () => {
    pauseDepth = Math.max(0, pauseDepth - 1);
  };
}

export function isChartPollingPaused(): boolean {
  if (pauseDepth > 0) return true;
  if (typeof document !== "undefined" && document.hidden) return true;
  return false;
}

/** @deprecated use acquireChartPolling */
export function setChartPollingPaused(paused: boolean): void {
  if (paused) pauseDepth += 1;
  else pauseDepth = Math.max(0, pauseDepth - 1);
}
