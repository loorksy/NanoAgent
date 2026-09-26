import type {
  ApiErrorBody,
  Approval,
  ApprovalDecision,
  ApprovalDecisionResponse,
  ApprovalStatus,
  CancelResponse,
  ConnectStatus,
  ControlResponse,
  CreateJobRequest,
  CreateSessionRequest,
  Device,
  Health,
  Job,
  JobCancelResponse,
  LabelsResponse,
  LiveRecommendationResponse,
  LogPage,
  LogQuery,
  Me,
  Mt5PermissionsPayload,
  Mt5PermissionsUpdate,
  PairDeviceRequest,
  PairDeviceResponse,
  PairingCode,
  RecommendationsPage,
  RecommendationsQuery,
  Recommendation,
  RegisterDeviceRequest,
  ResultRecord,
  ResultsPage,
  RiskField,
  RiskProfileName,
  RiskSettings,
  RiskUpdateRequest,
  SendMessageRequest,
  SendMessageResponse,
  Session,
  SessionStateDetail,
  StructuredType,
  TimelinePage,
} from "./types.ts";

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export type TokenSource = string | (() => string | undefined | Promise<string | undefined>);

export interface GatewayClientOptions {
  /** Origin of the gateway, e.g. `https://bot.example.com:8765`. */
  baseUrl: string;
  token?: TokenSource;
  /** Injected `fetch`; defaults to `globalThis.fetch`. */
  fetch?: FetchLike;
  /** Sent as `X-NanoAgent-Session` on every request when set. */
  session?: string;
  locale?: string;
  /** Defaults to `/api/v2`. */
  apiPrefix?: string;
  /** Defaults to `/ws/v2`. */
  wsPath?: string;
}

export class GatewayError extends Error {
  readonly status: number;
  readonly code: string;
  readonly messageKey: string;
  readonly details: Record<string, unknown> | undefined;

  constructor(status: number, body: ApiErrorBody["error"] | undefined, fallback: string) {
    super(body?.message_key ?? fallback);
    this.name = "GatewayError";
    this.status = status;
    this.code = body?.code ?? `http_${status}`;
    this.messageKey = body?.message_key ?? fallback;
    this.details = body?.details;
  }
}

type Query = Record<string, string | number | boolean | undefined | null>;

interface RequestOptions {
  body?: unknown;
  query?: Query;
  accept?: string;
  signal?: AbortSignal;
}

function trimTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function toQueryString(query: Query | undefined): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

async function parseErrorBody(response: Response): Promise<ApiErrorBody["error"] | undefined> {
  try {
    const parsed = (await response.json()) as Partial<ApiErrorBody> | null;
    if (parsed && typeof parsed === "object" && parsed.error && typeof parsed.error === "object") {
      return parsed.error;
    }
  } catch {
    /* non-JSON error body */
  }
  return undefined;
}

export class GatewayClient {
  readonly baseUrl: string;
  readonly apiPrefix: string;
  readonly wsPath: string;
  private token: TokenSource | undefined;
  private readonly fetchImpl: FetchLike;
  session: string | undefined;
  locale: string | undefined;

  constructor(options: GatewayClientOptions) {
    this.baseUrl = trimTrailingSlash(options.baseUrl);
    this.apiPrefix = options.apiPrefix ?? "/api/v2";
    this.wsPath = options.wsPath ?? "/ws/v2";
    this.token = options.token;
    this.session = options.session;
    this.locale = options.locale;
    const injected = options.fetch;
    if (injected) {
      this.fetchImpl = injected;
    } else {
      const globalFetch = globalThis.fetch;
      if (typeof globalFetch !== "function") {
        throw new Error("No fetch implementation available; pass `fetch` in options");
      }
      this.fetchImpl = (input, init) => globalFetch(input, init);
    }
  }

  setToken(token: TokenSource | undefined): void {
    this.token = token;
  }

  async resolveToken(): Promise<string | undefined> {
    const source = this.token;
    if (typeof source === "function") return source();
    return source;
  }

  url(path: string, query?: Query): string {
    return `${this.baseUrl}${this.apiPrefix}${path}${toQueryString(query)}`;
  }

  wsUrl(): string {
    const httpUrl = new URL(this.baseUrl);
    httpUrl.protocol = httpUrl.protocol === "https:" ? "wss:" : "ws:";
    return `${trimTrailingSlash(httpUrl.toString())}${this.wsPath}`;
  }

  async headers(extra?: Record<string, string>): Promise<Record<string, string>> {
    const headers: Record<string, string> = { Accept: "application/json", ...extra };
    const token = await this.resolveToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (this.session) headers["X-NanoAgent-Session"] = this.session;
    if (this.locale) headers["Accept-Language"] = this.locale;
    return headers;
  }

  /** Low-level access to the injected fetch (used by the SSE subscriber). */
  fetchStream(url: string, init: RequestInit): Promise<Response> {
    return this.fetchImpl(url, init);
  }

  async raw(method: string, path: string, options: RequestOptions = {}): Promise<Response> {
    const headers = await this.headers(options.accept ? { Accept: options.accept } : undefined);
    const init: RequestInit = { method, headers };
    if (options.signal) init.signal = options.signal;
    if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(options.body);
    }
    const response = await this.fetchImpl(this.url(path, options.query), init);
    if (!response.ok) {
      throw new GatewayError(response.status, await parseErrorBody(response), "error.http");
    }
    return response;
  }

  async request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
    const response = await this.raw(method, path, options);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  // -- identity --------------------------------------------------------------

  me(): Promise<Me> {
    return this.request("GET", "/me");
  }

  health(): Promise<Health> {
    return this.request("GET", "/health");
  }

  // -- sessions --------------------------------------------------------------

  async listSessions(options: { archived?: boolean } = {}): Promise<Session[]> {
    const page = await this.request<{ sessions: Session[] }>("GET", "/sessions", {
      query: { archived: options.archived ? "1" : undefined },
    });
    return page.sessions;
  }

  createSession(body: CreateSessionRequest = {}): Promise<Session> {
    return this.request("POST", "/sessions", { body });
  }

  getSession(id: string): Promise<Session> {
    return this.request("GET", `/sessions/${encodeURIComponent(id)}`);
  }

  deleteSession(id: string): Promise<void> {
    return this.request("DELETE", `/sessions/${encodeURIComponent(id)}`);
  }

  sendMessage(id: string, body: SendMessageRequest): Promise<SendMessageResponse> {
    return this.request("POST", `/sessions/${encodeURIComponent(id)}/messages`, { body });
  }

  cancel(id: string): Promise<CancelResponse> {
    return this.request("POST", `/sessions/${encodeURIComponent(id)}/cancel`);
  }

  getState(id: string): Promise<SessionStateDetail> {
    return this.request("GET", `/sessions/${encodeURIComponent(id)}/state`);
  }

  getTimeline(id: string, after?: string, limit?: number): Promise<TimelinePage> {
    return this.request("GET", `/sessions/${encodeURIComponent(id)}/timeline`, {
      query: { after, limit },
    });
  }

  /** URL of the SSE stream; `after` is also sent as `Last-Event-ID` by `subscribe`. */
  eventsUrl(id: string, after?: string): string {
    return this.url(`/sessions/${encodeURIComponent(id)}/events`, { after });
  }

  // -- approvals -------------------------------------------------------------

  async listApprovals(
    status: ApprovalStatus | undefined = "pending",
    limit?: number,
  ): Promise<Approval[]> {
    const page = await this.request<{ approvals: Omit<Approval, "approval_id">[] }>(
      "GET",
      "/approvals",
      { query: { status, limit } },
    );
    return page.approvals.map(withApprovalId);
  }

  async getApproval(id: string): Promise<Approval> {
    const record = await this.request<Omit<Approval, "approval_id">>(
      "GET",
      `/approvals/${encodeURIComponent(id)}`,
    );
    return withApprovalId(record);
  }

  async decideApproval(id: string, decision: ApprovalDecision): Promise<ApprovalDecisionResponse> {
    const record = await this.request<Omit<ApprovalDecisionResponse, "approval_id">>(
      "POST",
      `/approvals/${encodeURIComponent(id)}`,
      { body: { decision } },
    );
    return withApprovalId(record);
  }

  // -- jobs ------------------------------------------------------------------

  async listJobs(): Promise<Job[]> {
    const page = await this.request<{ jobs: Job[] }>("GET", "/jobs");
    return page.jobs;
  }

  getJob(id: string): Promise<Job> {
    return this.request("GET", `/jobs/${encodeURIComponent(id)}`);
  }

  createJob(body: CreateJobRequest): Promise<Job> {
    return this.request("POST", "/jobs", { body });
  }

  pauseJob(id: string): Promise<Job> {
    return this.request("POST", `/jobs/${encodeURIComponent(id)}/pause`);
  }

  resumeJob(id: string): Promise<Job> {
    return this.request("POST", `/jobs/${encodeURIComponent(id)}/resume`);
  }

  cancelJob(id: string): Promise<JobCancelResponse> {
    return this.request("POST", `/jobs/${encodeURIComponent(id)}/cancel`);
  }

  deleteJob(id: string): Promise<JobCancelResponse> {
    return this.request("DELETE", `/jobs/${encodeURIComponent(id)}`);
  }

  // -- recommendations -------------------------------------------------------

  /** Latest live plan of one session (the gateway scopes live plans per session). */
  async getLiveRecommendation(session: string): Promise<Recommendation | null> {
    const response = await this.request<LiveRecommendationResponse>("GET", "/recommendations/live", {
      query: { session },
    });
    return response.live;
  }

  async listRecommendations(query: RecommendationsQuery = {}): Promise<Recommendation[]> {
    const page = await this.request<RecommendationsPage>("GET", "/recommendations", {
      query: {
        from: query.from,
        to: query.to,
        session: query.session,
        status: query.status,
        limit: query.limit,
      },
    });
    return page.recommendations;
  }

  getRecommendation(id: string): Promise<Recommendation> {
    return this.request("GET", `/recommendations/${encodeURIComponent(id)}`);
  }

  // -- connect / control -----------------------------------------------------

  getConnect(): Promise<ConnectStatus> {
    return this.request("GET", "/connect");
  }

  getControl(): Promise<ControlResponse> {
    return this.request("GET", "/control");
  }

  /** Kill switch: `enabled=false` releases it. */
  kill(enabled = true): Promise<ControlResponse> {
    return this.request("POST", "/control/kill", { body: { enabled } });
  }

  pause(paused: boolean): Promise<ControlResponse> {
    return paused
      ? this.request("POST", "/control/pause", { body: { enabled: true } })
      : this.request("POST", "/control/resume");
  }

  setPaperMode(enabled: boolean): Promise<ControlResponse> {
    return this.request("POST", "/control/paper-mode", { body: { enabled } });
  }

  getRisk(): Promise<RiskSettings> {
    return this.request("GET", "/connect/risk");
  }

  setRiskProfile(name: RiskProfileName): Promise<RiskSettings> {
    return this.request("PUT", "/connect/risk-profile", { body: { name } });
  }

  setRiskField(field: RiskField | string, value: number, derive = true): Promise<RiskSettings> {
    return this.request("PUT", `/connect/risk/${encodeURIComponent(field)}`, {
      body: { value, derive },
    });
  }

  updateRisk(body: RiskUpdateRequest): Promise<RiskSettings> {
    return this.request("PUT", "/connect/risk", { body });
  }

  getMt5Permissions(): Promise<Mt5PermissionsPayload> {
    return this.request("GET", "/connect/mt5/permissions");
  }

  setMt5Permissions(update: Mt5PermissionsUpdate, who?: string): Promise<Mt5PermissionsPayload> {
    return this.request("PUT", "/connect/mt5/permissions", { body: { permissions: update, who } });
  }

  // -- log / labels ----------------------------------------------------------

  getLog(query: LogQuery = {}): Promise<LogPage> {
    return this.request("GET", "/log", {
      query: {
        kinds: query.kinds && query.kinds.length > 0 ? query.kinds.join(",") : undefined,
        from: query.from,
        limit: query.limit,
        session: query.session,
      },
    });
  }

  getLabels(locale: string, prefix?: string): Promise<LabelsResponse> {
    return this.request("GET", "/labels", { query: { locale, prefix } });
  }

  // -- results ---------------------------------------------------------------

  listResults(query: { session?: string; type?: StructuredType; limit?: number } = {}): Promise<ResultsPage> {
    return this.request("GET", "/results", { query: { ...query } });
  }

  getResult(id: string): Promise<ResultRecord> {
    return this.request("GET", `/results/${encodeURIComponent(id)}`);
  }

  async getResultHtml(id: string, locale?: string): Promise<string> {
    const response = await this.raw("GET", `/results/${encodeURIComponent(id)}/html`, {
      query: { locale },
      accept: "text/html",
    });
    return response.text();
  }

  // -- devices ---------------------------------------------------------------

  registerDevice(body: RegisterDeviceRequest): Promise<Device> {
    return this.request("POST", "/devices", { body });
  }

  async listDevices(includeRevoked = false): Promise<Device[]> {
    const page = await this.request<{ devices: Device[] }>("GET", "/devices", {
      query: { revoked: includeRevoked ? "1" : undefined },
    });
    return page.devices;
  }

  /** Public: exchange a pairing code for a long-lived device token (no bearer needed). */
  pairDevice(body: PairDeviceRequest): Promise<PairDeviceResponse> {
    return this.request("POST", "/devices/pair", { body });
  }

  /** Admin only. */
  createPairingCode(body: { label?: string; ttl_seconds?: number } = {}): Promise<PairingCode> {
    return this.request("POST", "/devices/pairing-codes", { body });
  }

  deleteDevice(id: string): Promise<{ deleted: boolean; id: string }> {
    return this.request("DELETE", `/devices/${encodeURIComponent(id)}`);
  }
}

function withApprovalId<T extends { id: string }>(record: T): T & { approval_id: string } {
  return { ...record, approval_id: record.id };
}
