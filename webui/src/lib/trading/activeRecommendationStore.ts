import { useEffect, useState } from "react";

export interface ActiveRecommendationLine {
  id: string;
  kind: "entry" | "sl" | "tp";
  price: number;
  state: "active" | "hit" | "invalidated";
  label?: string;
}

export interface ActiveRecommendationState {
  id: string;
  direction: string;
  entry: number | null;
  stopLoss: number | null;
  targets: number[];
  status: string;
}

interface StoreSnapshot {
  active: ActiveRecommendationState | null;
  lines: ActiveRecommendationLine[];
}

let snapshot: StoreSnapshot = { active: null, lines: [] };
const listeners = new Set<() => void>();

function buildLines(rec: ActiveRecommendationState): ActiveRecommendationLine[] {
  const lines: ActiveRecommendationLine[] = [];
  if (rec.entry != null) {
    lines.push({ id: `${rec.id}-entry`, kind: "entry", price: rec.entry, state: "active", label: "Entry" });
  }
  if (rec.stopLoss != null) {
    lines.push({ id: `${rec.id}-sl`, kind: "sl", price: rec.stopLoss, state: "active", label: "SL" });
  }
  rec.targets.forEach((price, index) => {
    lines.push({
      id: `${rec.id}-tp${index + 1}`,
      kind: "tp",
      price,
      state: "active",
      label: `TP${index + 1}`,
    });
  });
  return lines;
}

function notify() {
  for (const listener of listeners) listener();
}

export function getActiveRecommendation(): StoreSnapshot {
  return snapshot;
}

export function subscribeActiveRecommendation(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function setActiveRecommendation(rec: ActiveRecommendationState | null): void {
  snapshot = {
    active: rec,
    lines: rec ? buildLines(rec) : [],
  };
  notify();
}

export function clearActiveRecommendation(): void {
  snapshot = { active: null, lines: [] };
  notify();
}

export function useActiveRecommendation(): StoreSnapshot {
  const [state, setState] = useState(snapshot);
  useEffect(() => {
    const sync = () => setState(getActiveRecommendation());
    sync();
    return subscribeActiveRecommendation(sync);
  }, []);
  return state;
}
