export interface TradingStageWire {
  stage: string;
  status: string;
  timestamp?: number;
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
  keyReasons?: string[];
  riskWarnings?: string[];
  recommendationId?: string;
  cards?: Array<Record<string, unknown>>;
  stages?: TradingStageWire[];
  teamMode?: string;
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

export interface TradingSessionState {
  chartOpen: boolean;
  interval: string;
  stages: TradingStageWire[];
  result: TradingResultWire | null;
}
