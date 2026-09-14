export interface TradingArtifact {
  type: string;
  title?: string;
  mime?: string;
  payload?: Record<string, unknown>;
}

export interface TradingStageWire {
  stage: string;
  status: string;
  timestamp?: number;
  durationMs?: number;
}

export interface TradingTeamAgentWire {
  agentId: string;
  role: string;
  status: "running" | "done" | "failed" | string;
  summary?: string;
  layer?: number;
  durationMs?: number;
}

export interface TradingRecommendationWire {
  action?: string;
  entry?: number;
  stopLoss?: number;
  targets?: number[];
  planType?: string;
  executionState?: string;
}

export interface TradingMacroDriverWire {
  driver?: string;
  name?: string;
  bias?: string;
  strength?: number;
  one_line_rationale?: string;
  source?: string;
  ran?: boolean;
  reason?: string;
}

export interface TradingResultWire {
  decision: string;
  confidence: number;
  summary: string;
  artifactOnly?: boolean;
  locale?: string;
  keyReasons?: string[];
  riskWarnings?: string[];
  recommendationId?: string;
  artifacts?: TradingArtifact[];
  cards?: Array<Record<string, unknown>>;
  stages?: TradingStageWire[];
  teamMode?: string;
  teamAgents?: TradingTeamAgentWire[];
  macroDrivers?: TradingMacroDriverWire[];
  drawings?: Array<Record<string, unknown>>;
  interval?: string;
  recommendation?: TradingRecommendationWire;
  gateChain?: {
    allowed: boolean;
    confidenceDelta?: number;
    verdicts?: Array<Record<string, unknown>>;
  };
  refusalSummary?: string;
}

export interface TradingOutcomeWire {
  recommendationId: string;
  previousStatus?: string;
  outcomeStatus: string;
  direction: string;
  summary: string;
  livePrice?: number | null;
}

export interface TradingChartCaptureWire {
  captureId: string;
  sessionKey: string;
  timeframes: string[];
}

export interface TradingSessionState {
  chartOpen: boolean;
  interval: string;
  stages: TradingStageWire[];
  teamAgents: TradingTeamAgentWire[];
  result: TradingResultWire | null;
  chartCapture: TradingChartCaptureWire | null;
  outcomeAlerts: TradingOutcomeWire[];
}
