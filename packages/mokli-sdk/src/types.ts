/**
 * Public contract of the Mokli Agent Gateway (docs/designs/mokli-v2/07-agent-gateway.md).
 *
 * Every shape here mirrors §4 (event contract), §5 (structured results), §6 (REST) and §8 (auth).
 * No user-facing text lives in this file: labels are resolved through `GET /labels?locale=`.
 */

// ---------------------------------------------------------------------------
// Agent state (§3)
// ---------------------------------------------------------------------------

export type AgentState = "working" | "waiting" | "completed";

export type RunOutcome = "ok" | "cancelled" | "error" | "expired";

export type WaitingFor =
  | { kind: "approval"; id: string }
  | { kind: "input"; id?: string; prompt_key?: string };

export interface StateData {
  state: AgentState;
  phase?: string;
  waiting_for?: WaitingFor;
  outcome?: RunOutcome;
  /** Set only when the provider sent a reasoning delta for this phase. */
  provider_thinking?: boolean;
}

// ---------------------------------------------------------------------------
// Structured results (§5)
// ---------------------------------------------------------------------------

export type StructuredType =
  | "market"
  | "analysis"
  | "scenarios"
  | "risk"
  | "decision"
  | "approval"
  | "plan_status"
  | "scorecard";

export type FeedStatus = "connected" | "degraded" | "disconnected";

export interface MarketPayload {
  price: number;
  spread: number;
  session: string;
  dxy: number | null;
  yields: number | null;
  next_event?: { time: number; impact: "low" | "medium" | "high"; title_key?: string } | null;
  feed_status: FeedStatus;
}

export interface PriceZone {
  low: number;
  high: number;
  label_key?: string;
  timeframe?: string;
}

export interface LiquidityLevel {
  level: number;
  side: "buy" | "sell";
  label_key?: string;
}

export interface AnalysisPayload {
  htf_bias: "bullish" | "bearish" | "neutral";
  structure: string;
  zones: PriceZone[];
  fvg: PriceZone[];
  liquidity: LiquidityLevel[];
  momentum_score: number;
  confluence: string[];
}

export type Direction = "buy" | "sell";

export interface Scenario {
  direction: Direction;
  trigger: string;
  invalidation: string;
}

export interface ScenariosPayload {
  primary: Scenario;
  alternate: Scenario;
  active?: "primary" | "alternate";
}

export interface RiskBlocker {
  gate: string;
  reason_key: string;
}

export interface RiskPayload {
  risk_pct: number;
  lot: number;
  rr: number;
  daily_dd_used_pct: number;
  open_positions: number;
  blockers: RiskBlocker[];
}

export type Verdict = "buy" | "sell" | "wait";

export interface DecisionPayload {
  verdict: Verdict;
  entry: number | null;
  stop: number | null;
  targets: number[];
  confidence: number | null;
  reasons: string[];
  gates_passed: string[];
  permission_level?: PermissionLevel | null;
  plan_id?: string | null;
  summary?: string;
  entry_zone?: { low: number; high: number };
  risk_pct?: number;
  rr?: number | null;
  net_rr?: number | null;
  agreement?: { stance: Verdict; agreeing: number; votes: number };
  invalidation?: string;
  validity_candles?: number;
  data_sources?: string[];
  blockers?: string[];
  alternative?: string;
}

export type ApprovalType = "execution" | "modify" | "close" | "generic";
export type ApprovalAction = "confirm" | "cancel";
export type PermissionLevel = "recommend" | "propose" | "execute";

export interface ApprovalData {
  approval_id: string;
  type: ApprovalType;
  summary: string;
  expires_at: number | null;
  /** Empty once the approval is resolved. */
  actions?: ApprovalAction[];
  /** Present on gateway events; repeated with the final status when resolved. */
  status?: ApprovalStatus;
}

export interface ApprovalPayload extends ApprovalData {
  permission_level: PermissionLevel;
}

export type PlanState =
  | "draft"
  | "armed"
  | "in_trade"
  | "tp1"
  | "closed"
  | "invalidated"
  | "expired";

export interface PlanTransition {
  from: PlanState;
  to: PlanState;
  ts: number;
  reason_key?: string;
}

export interface PlanStatusPayload {
  plan_id: string;
  state: PlanState;
  transitions: PlanTransition[];
  pnl?: number | null;
}

export interface ScorecardPayload {
  period: string;
  trades: number;
  win_rate: number;
  expectancy: number;
  max_dd: number;
  notes_keys: string[];
}

export interface StructuredPayloadMap {
  market: MarketPayload;
  analysis: AnalysisPayload;
  scenarios: ScenariosPayload;
  risk: RiskPayload;
  decision: DecisionPayload;
  approval: ApprovalPayload;
  plan_status: PlanStatusPayload;
  scorecard: ScorecardPayload;
}

export type StructuredData = {
  [K in StructuredType]: { type: K; result_id: string; payload: StructuredPayloadMap[K] };
}[StructuredType];

export type StructuredResult = StructuredData & { session?: string; ts?: number };

// ---------------------------------------------------------------------------
// Event contract (§4)
// ---------------------------------------------------------------------------

export interface DeltaData {
  text: string;
}

export type ToolEventPhase = "started" | "finished" | "failed";

export interface ToolData {
  event: ToolEventPhase;
  name: string;
  call_id: string;
  summary?: string;
  duration_ms?: number;
  display?: string;
  arguments?: string;
}

export interface SubagentData {
  event: "started" | "finished" | "failed";
  id: string;
  role: string;
  display?: string;
  summary?: string;
  duration_ms?: number;
}

export interface ArtifactData {
  artifact_id: string;
  mime: string;
  url: string;
  title: string;
}

export type NotificationLevel = "info" | "warning" | "error";

/**
 * `title` / `body` are label keys (resolve them through `GET /labels`), never prose;
 * `args` carries the interpolation values.
 */
export interface NotificationData {
  level: NotificationLevel;
  title: string;
  body: string;
  args?: Record<string, string | number | boolean | null>;
  deep_link?: string;
}

export type JobKind = "cron" | "goal";
export type JobStatus =
  | "scheduled"
  | "working"
  | "waiting"
  | "paused"
  | "finished"
  | "failed"
  | "cancelled";

export interface JobData {
  job_id: string;
  kind: JobKind;
  status: JobStatus | string;
  progress?: JobProgress | null;
  next_run_at?: number | null;
  name?: string;
}

export interface EndData {
  run: string;
  outcome: RunOutcome;
}

export interface RetryData {
  state: "waiting" | "recovered" | "cleared" | "exhausted" | "cancelled";
  attempt: number;
  error_kind: string;
  max_attempts?: number;
}

export interface EventDataMap {
  delta: DeltaData;
  state: StateData;
  tool: ToolData;
  subagent: SubagentData;
  structured: StructuredData;
  artifact: ArtifactData;
  approval: ApprovalData;
  notification: NotificationData;
  job: JobData;
  end: EndData;
  retry: RetryData;
}

export type EventKind = keyof EventDataMap;

export interface GatewayEventBase {
  /** Monotonic ULID; used for `Last-Event-ID` replay. */
  id: string;
  session: string;
  run?: string;
  ts: number;
}

export type GatewayEvent = {
  [K in EventKind]: GatewayEventBase & { kind: K; data: EventDataMap[K] };
}[EventKind];

export type GatewayEventOf<K extends EventKind> = Extract<GatewayEvent, { kind: K }>;

// ---------------------------------------------------------------------------
// REST resources (§6)
// ---------------------------------------------------------------------------

export type Scope = "chat" | "read" | "approve" | "control" | "push" | "admin";

export type ClientKind = "web" | "device" | "service";

export type TextDirection = "ltr" | "rtl";

export interface Me {
  client_id: string;
  kind: ClientKind;
  scopes: Scope[];
  locale: string;
  label?: string;
  dir?: TextDirection;
  server?: { version: string; api: string; token_ttl_seconds?: number };
}

export interface Health {
  ok: boolean;
  version: string;
  api: string;
  sessions_running?: number;
}

export interface Session {
  id: string;
  title?: string | null;
  created_at: number;
  updated_at?: number;
  archived?: boolean;
  /** Current agent state (`working` / `waiting` / `completed`). */
  state?: AgentState;
  state_detail?: SessionStateDetail;
}

export interface SessionStateDetail extends StateData {
  session?: string;
  run?: string | null;
  updated_at?: number;
  pending_approvals?: string[];
  last_event_id?: string | null;
}

export interface CreateSessionRequest {
  title?: string;
  /** Client-chosen id (also accepted from the `X-Mokli-Session` header). */
  id?: string;
}

export type MessageContentPart =
  | { type: "text"; text: string }
  | { type: "image"; url?: string; base64?: string; mime: string }
  | { type: "audio"; url?: string; base64?: string; mime: string };

export interface SendMessageRequest {
  text?: string;
  parts?: MessageContentPart[];
  locale?: string;
}

export interface SendMessageResponse {
  run_id: string;
  session?: string;
}

export interface CancelResponse {
  cancelled: boolean;
  state?: SessionStateDetail;
}

export type TimelineEvent = GatewayEventOf<"tool" | "subagent" | "structured" | "artifact" | "approval">;

export interface TimelinePage {
  events: TimelineEvent[];
  next_after?: string | null;
}

/** Free-form progress blob for goal jobs (`ui_summary`, `recap`, `objective`, ...). */
export type JobProgress = Record<string, string | number | boolean | null>;

export interface Job {
  job_id: string;
  kind: JobKind;
  name?: string;
  status: JobStatus | string;
  progress?: JobProgress | null;
  next_run_at?: number | null;
  last_run_at?: number | null;
  last_status?: string | null;
  session?: string | null;
}

export interface CreateJobRequest {
  kind: JobKind;
  name: string;
  schedule?: string;
  prompt?: string;
  session?: string;
}

export interface JobCancelResponse {
  job_id: string;
  status: "cancelled";
}

export type ApprovalStatus = "pending" | "confirmed" | "cancelled" | "expired" | "auto_confirmed";

export type ApprovalDecision = ApprovalAction;

/** REST view of an approval (`GET /approvals`). Events carry {@link ApprovalData} instead. */
export interface Approval {
  id: string;
  /** Same as `id`; filled in by the client so REST and event shapes can be mixed. */
  approval_id: string;
  session: string | null;
  run: string | null;
  type: ApprovalType;
  status: ApprovalStatus;
  summary: string;
  created_at: number;
  expires_at: number | null;
  resolved_at: number | null;
  decision: ApprovalDecision | null;
  source_id: string | null;
  details: Record<string, unknown>;
}

export interface ApprovalDecisionRequest {
  decision: ApprovalDecision;
}

export interface ApprovalDecisionResponse extends Approval {
  decided_by?: string;
}

export type RecommendationStatus = "live" | "closed" | "archived" | string;

/** Row of the trading recommendation store (`mokli/trading/recommendations/store.py`). */
export interface Recommendation {
  id: string;
  symbol: string;
  interval: string | null;
  direction: Direction | string;
  entry: number | null;
  stop_loss: number | null;
  targets: number[];
  status: RecommendationStatus;
  summary: string | null;
  confidence: number | null;
  created_at: number;
  session: string | null;
  closed_at?: number | null;
  close_reason?: string | null;
  archive_category?: string | null;
}

export interface RecommendationsQuery {
  from?: number;
  to?: number;
  session?: string;
  status?: string;
  limit?: number;
}

export interface LiveRecommendationResponse {
  live: Recommendation | null;
  session: string;
}

export interface RecommendationsPage {
  recommendations: Recommendation[];
  count: number;
}

export type RiskProfileName = "conservative" | "balanced" | "aggressive";

/** The seven primary risk fields (04-ui-redesign §4.2). */
export interface RiskFields {
  risk_pct_default: number;
  daily_drawdown_pct: number;
  max_open_gold_positions: number;
  min_rr: number;
  news_shield_minutes: number;
  cooldown_after_two_losses_minutes: number;
  spread_max_points: number;
}

export type RiskField = keyof RiskFields;

export const RISK_FIELDS: readonly RiskField[] = [
  "risk_pct_default",
  "daily_drawdown_pct",
  "max_open_gold_positions",
  "min_rr",
  "news_shield_minutes",
  "cooldown_after_two_losses_minutes",
  "spread_max_points",
] as const;

export type TradingSession = "london" | "newyork" | "asia" | "overlap";

/** Mirrors `mokli/trading/permissions/model.py::Mt5Permissions` (08 §3). */
export interface Mt5Permissions {
  level: PermissionLevel;
  can_open: boolean;
  can_modify_sl_tp: boolean;
  allow_widen_stop: boolean;
  can_partial_close: boolean;
  can_close_all: boolean;
  can_place_pending: boolean;
  max_lot_per_order: number | null;
  max_lot_hard?: boolean;
  max_total_lots: number | null;
  auto_daily_loss_pct: number | null;
  sessions: TradingSession[];
  news_lock: boolean;
  expires_at: number | null;
  grace_hours: number;
  granted_at: number;
  granted_by: string;
  upgrade_requires_biometric?: boolean;
}

export type Mt5PermissionsUpdate = Partial<Omit<Mt5Permissions, "granted_at" | "granted_by">>;

export interface Mt5PermissionAudit {
  ts: number;
  who?: string;
  changes?: Record<string, unknown>;
  [key: string]: unknown;
}

/** `GET /connect/mt5/permissions` and the result of `PUT`. */
export interface Mt5PermissionsPayload {
  permissions: Mt5Permissions;
  /** Grant with limits derived from the active risk profile. */
  effective: Mt5Permissions;
  audit?: Mt5PermissionAudit[];
  levels: { name: PermissionLevel; label: string }[];
  actions: string[];
  sessions: { name: TradingSession | string; start_hour_utc: number; end_hour_utc: number }[];
  last_action?: Record<string, unknown>;
}

export interface Mt5PermissionsUpdateRequest {
  permissions: Mt5PermissionsUpdate;
  who?: string;
}

/** `mokli/trading/runtime_state.py::TradingRuntimeState`. */
export interface RuntimeState {
  paused: boolean;
  kill_switch: boolean;
  paper_mode: boolean;
}

export type RuntimeField = "paused" | "kill_switch" | "paper_mode";

export interface ControlResponse {
  runtime_state: RuntimeState;
  changed?: RuntimeField;
  enabled?: boolean;
}

export interface RiskFieldSlider {
  min: number;
  max: number;
  step: number;
}

export interface RiskFieldDescriptor {
  name: RiskField | string;
  label: string;
  group: string;
  group_label: string;
  unit: string;
  value: number;
  type: "integer" | "number";
  step: number;
  tier?: string;
  derived: boolean;
  min?: number;
  max?: number;
  slider?: RiskFieldSlider;
}

export interface RiskGroup {
  id: string;
  label: string;
  fields: RiskFieldDescriptor[];
}

export interface RiskProfileInfo {
  name: RiskProfileName | "custom" | string;
  detected: RiskProfileName | "custom" | string | null;
  presets: { name: RiskProfileName; label: string; values: Record<string, number> }[];
  names: string[];
  slider_fields: string[];
  derived_fields: string[];
}

export type RiskToggles = Record<string, boolean>;

/** `GET /connect/risk` (also returned by the risk mutations). */
export interface RiskPayload_ {
  values: RiskFields & Record<string, number | string | boolean | null>;
  groups: RiskGroup[];
  toggles: RiskToggles;
  locked_toggles: string[];
  profile: RiskProfileInfo;
  title?: string;
  description?: string;
  last_action?: Record<string, unknown>;
}

export type RiskSettings = RiskPayload_;

export interface RiskUpdateRequest {
  values?: Partial<RiskFields> & Record<string, number | string | boolean | null>;
  toggles?: RiskToggles;
  derive?: boolean;
}

export interface Mt5BrokerStatus {
  configured: boolean;
  connected?: boolean;
  host: string;
  port: number;
  login: string;
  server: string;
  password_set: boolean;
  name?: string;
}

export interface BrokerStatus {
  oanda: { configured: boolean; env: string; account_id: string };
  mt5: Mt5BrokerStatus;
}

export interface RiskRuntimeState {
  consecutive_losses: number;
  cooldown_until_ms: number | null;
  cooldown_reason: string | null;
  daily_pnl_pct: number;
  open_positions: number;
  emergency_lock: boolean;
  news_day: boolean;
  holiday: boolean;
  feature_toggles: RiskToggles;
}

/** `GET /connect`. */
export interface ConnectStatus {
  brokers: BrokerStatus;
  runtime_state: RuntimeState;
  risk_state: RiskRuntimeState;
  risk: Pick<RiskSettings, "profile" | "values" | "groups" | "toggles" | "locked_toggles">;
  mt5_permissions: Pick<Mt5PermissionsPayload, "permissions" | "effective" | "levels" | "actions" | "sessions">;
}

export type LogKind =
  | "decision"
  | "execution"
  | "gate"
  | "approval"
  | "permission"
  | "job"
  | "notification"
  | "structured";

export const LOG_KINDS: readonly LogKind[] = [
  "decision",
  "execution",
  "gate",
  "approval",
  "permission",
  "job",
  "notification",
  "structured",
] as const;

export type LogSource = "gateway" | "trades.jsonl" | "mt5_permissions" | string;

export interface LogEntry {
  id: string;
  ts: number;
  kind: LogKind;
  source: LogSource;
  /** Event data (`tool` / `approval` / ...), a decision row, or a permission audit row. */
  data: Record<string, unknown> & { session?: string | null; run?: string | null };
}

export interface LogQuery {
  kinds?: LogKind[];
  from?: number;
  limit?: number;
  session?: string;
}

export interface LogPage {
  entries: LogEntry[];
  kinds: LogKind[];
  count: number;
}

export type Labels = Record<string, string>;

export interface LabelsResponse {
  locale: string;
  dir: TextDirection;
  supported: string[];
  labels: Labels;
}

/** `GET /results/{id}` — persisted structured result. */
export interface ResultRecord {
  id: string;
  session: string | null;
  run: string | null;
  type: StructuredType;
  ts: number;
  payload: Record<string, unknown>;
}

export interface ResultsPage {
  results: ResultRecord[];
  types: StructuredType[];
}

export type DevicePlatform = "ios" | "android" | "web";

export interface RegisterDeviceRequest {
  platform: DevicePlatform;
  push_token: string;
  label?: string;
  locale?: string;
}

export interface Device {
  id: string;
  client_id: string;
  platform: DevicePlatform;
  label: string;
  locale: string;
  created_at: number;
  updated_at: number;
  revoked: boolean;
}

export interface ClientRecord {
  id: string;
  kind: ClientKind;
  scopes: Scope[];
  label: string;
  locale: string;
  created_at: number;
  revoked_at: number | null;
}

export interface PairDeviceRequest {
  code: string;
  label?: string;
  locale?: string;
  /** When both are given the push token is registered in the same call. */
  platform?: DevicePlatform;
  push_token?: string;
}

export interface PairDeviceResponse {
  token: string;
  expires_at: number | null;
  client: ClientRecord;
  device?: Device;
}

export interface PairingCode {
  code: string;
  expires_at: number;
  pair_url: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message_key: string;
    details?: Record<string, unknown>;
  };
}

// ---------------------------------------------------------------------------
// WebSocket (§4)
// ---------------------------------------------------------------------------

export type WsClientMessage =
  | { type: "subscribe"; session: string; after?: string }
  | { type: "unsubscribe"; session: string }
  | { type: "send"; session: string; text?: string; parts?: MessageContentPart[]; request_id?: string }
  | { type: "cancel"; session: string }
  | { type: "approve"; session?: string; approval_id: string; decision: ApprovalDecision }
  | { type: "ping"; ts?: number };

export type WsServerMessage =
  | { type: "event"; event: GatewayEvent }
  | { type: "pong"; ts?: number }
  | { type: "ack"; request_id?: string; run_id?: string }
  | { type: "error"; error: ApiErrorBody["error"]; request_id?: string };

// ---------------------------------------------------------------------------
// Push payload (§7) — no prices or levels ever appear here.
// ---------------------------------------------------------------------------

/** `kind` values produced by `payload_for` in `mokli/agent_api/push/router.py`. */
export type PushKind = "approval" | "notification" | "decision" | "job" | "agent_message";

export interface PushPayload {
  kind: PushKind;
  title_key: string;
  body_key: string;
  args?: Record<string, string | number>;
  session?: string;
  deep_link?: string;
  approval_id?: string;
}
