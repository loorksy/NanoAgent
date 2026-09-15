import type {
  SupersedeDecisionWire,
  TradingChartCaptureWire,
  TradingOutcomeWire,
  TradingResultWire,
  TradingSessionState,
  TradingStageWire,
  TradingTeamAgentWire,
} from "@/lib/trading/types";

const DEFAULT_STATE: TradingSessionState = {
  chartOpen: false,
  interval: "15m",
  stages: [],
  teamAgents: [],
  result: null,
  chartCapture: null,
  outcomeAlerts: [],
  supersedeDecision: null,
};

const sessions = new Map<string, TradingSessionState>();
const listeners = new Set<(chatId: string) => void>();

function snapshot(chatId: string): TradingSessionState {
  return sessions.get(chatId) ?? DEFAULT_STATE;
}

function notify(chatId: string) {
  for (const listener of listeners) listener(chatId);
}

export function getTradingSession(chatId: string): TradingSessionState {
  return snapshot(chatId);
}

export function subscribeTradingSession(listener: (chatId: string) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function setTradingChartOpen(chatId: string, chartOpen: boolean) {
  const prev = snapshot(chatId);
  sessions.set(chatId, {
    ...prev,
    chartOpen,
  });
  notify(chatId);
}

export function pushTradingOutcome(chatId: string, alert: TradingOutcomeWire) {
  const prev = snapshot(chatId);
  const key = `${alert.recommendationId}-${alert.outcomeStatus}`;
  const outcomeAlerts = prev.outcomeAlerts.filter(
    (row) => `${row.recommendationId}-${row.outcomeStatus}` !== key,
  );
  outcomeAlerts.unshift(alert);
  sessions.set(chatId, {
    ...prev,
    outcomeAlerts: outcomeAlerts.slice(0, 5),
  });
  notify(chatId);
}

export function dismissTradingOutcome(chatId: string, alertKey: string) {
  const prev = snapshot(chatId);
  sessions.set(chatId, {
    ...prev,
    outcomeAlerts: prev.outcomeAlerts.filter(
      (row) => `${row.recommendationId}-${row.outcomeStatus}` !== alertKey,
    ),
  });
  notify(chatId);
}

export function openTradingChart(chatId: string, interval = "15m") {
  const prev = snapshot(chatId);
  sessions.set(chatId, {
    ...prev,
    chartOpen: true,
    interval,
  });
  notify(chatId);
}

export function pushTradingTeamAgent(chatId: string, agent: TradingTeamAgentWire) {
  const prev = snapshot(chatId);
  const teamAgents = [...prev.teamAgents];
  const index = teamAgents.findIndex((row) => row.agentId === agent.agentId);
  if (index >= 0) {
    teamAgents[index] = agent;
  } else {
    teamAgents.push(agent);
  }
  sessions.set(chatId, {
    ...prev,
    chartOpen: true,
    teamAgents,
  });
  notify(chatId);
}

export function pushTradingStage(chatId: string, stage: TradingStageWire) {
  const prev = snapshot(chatId);
  const stages = [...prev.stages];
  const index = stages.findIndex((row) => row.stage === stage.stage);
  if (index >= 0) {
    stages[index] = stage;
  } else {
    stages.push(stage);
  }
  sessions.set(chatId, {
    ...prev,
    chartOpen: true,
    stages,
  });
  notify(chatId);
}

export function setTradingResult(chatId: string, result: TradingResultWire) {
  const prev = snapshot(chatId);
  sessions.set(chatId, {
    ...prev,
    chartOpen: true,
    interval: result.interval ?? prev.interval,
    result,
  });
  notify(chatId);
}

export function requestChartCapture(chatId: string, capture: TradingChartCaptureWire) {
  const prev = snapshot(chatId);
  sessions.set(chatId, {
    ...prev,
    chartOpen: true,
    chartCapture: capture,
  });
  notify(chatId);
}

export function clearChartCapture(chatId: string) {
  const prev = snapshot(chatId);
  if (!prev.chartCapture) return;
  sessions.set(chatId, {
    ...prev,
    chartCapture: null,
  });
  notify(chatId);
}

export function pushSupersedeDecision(chatId: string, payload: SupersedeDecisionWire) {
  const prev = snapshot(chatId);
  sessions.set(chatId, {
    ...prev,
    supersedeDecision: payload,
  });
  notify(chatId);
}

export function clearSupersedeDecision(chatId: string) {
  const prev = snapshot(chatId);
  if (!prev.supersedeDecision) return;
  sessions.set(chatId, {
    ...prev,
    supersedeDecision: null,
  });
  notify(chatId);
}

export function resetTradingSession(chatId: string) {
  sessions.delete(chatId);
  notify(chatId);
}

export const TRADING_CHART_PANE_PREFIX = "trading-chart:";

export function tradingChartPaneKey(anchorPaneKey: string): string {
  return `${TRADING_CHART_PANE_PREFIX}${anchorPaneKey}`;
}

export function isTradingChartPaneKey(key: string): boolean {
  return key.startsWith(TRADING_CHART_PANE_PREFIX);
}

export function anchorPaneKeyFromTradingChart(key: string): string {
  return key.slice(TRADING_CHART_PANE_PREFIX.length);
}
