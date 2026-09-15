/** Browser-wide wake signal for live chart pipes (AiChart pattern). */
export const APP_WAKE_EVENT = "nanobot:app-wake";

const TICK_RECONNECT_BASE_MS = 400;
const TICK_RECONNECT_MAX_MS = 8_000;
const WAKE_DEDUPE_MS = 1_000;

let started = false;
let lastWakeAt = 0;

export function tickReconnectDelayMs(attempt: number): number {
  const n = Number.isFinite(attempt) ? Math.max(0, Math.floor(attempt)) : 0;
  return Math.min(TICK_RECONNECT_MAX_MS, TICK_RECONNECT_BASE_MS * 2 ** n);
}

export function dispatchAppWake(): void {
  if (typeof window === "undefined") return;
  const now = Date.now();
  if (now - lastWakeAt < WAKE_DEDUPE_MS) return;
  lastWakeAt = now;
  window.dispatchEvent(new Event(APP_WAKE_EVENT));
}

export function startAppWakeBridge(): () => void {
  if (typeof window === "undefined" || started) return () => {};
  started = true;
  const onVisible = () => {
    if (document.visibilityState === "visible") dispatchAppWake();
  };
  window.addEventListener("focus", dispatchAppWake);
  window.addEventListener("online", dispatchAppWake);
  window.addEventListener("pageshow", dispatchAppWake);
  document.addEventListener("visibilitychange", onVisible);
  return () => {
    started = false;
    window.removeEventListener("focus", dispatchAppWake);
    window.removeEventListener("online", dispatchAppWake);
    window.removeEventListener("pageshow", dispatchAppWake);
    document.removeEventListener("visibilitychange", onVisible);
  };
}
