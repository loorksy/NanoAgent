export class ChartHostWsClient {
  private socket: WebSocket | null = null;
  private readonly token: string;
  private readonly wsPath: string;

  constructor(token: string, wsPath = "/") {
    this.token = token;
    this.wsPath = wsPath;
  }

  async connect(): Promise<void> {
    if (this.socket?.readyState === WebSocket.OPEN) return;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}${this.wsPath}?token=${encodeURIComponent(this.token)}&client_id=chart-host`;
    await new Promise<void>((resolve, reject) => {
      const socket = new WebSocket(url);
      const timer = window.setTimeout(() => {
        socket.close();
        reject(new Error("chart-host websocket timeout"));
      }, 10_000);
      socket.onopen = () => {
        window.clearTimeout(timer);
        this.socket = socket;
        resolve();
      };
      socket.onerror = () => {
        window.clearTimeout(timer);
        reject(new Error("chart-host websocket failed"));
      };
    });
  }

  async submitCapture(captureId: string, frames: unknown[]): Promise<void> {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      await this.connect();
    }
    const socket = this.socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      throw new Error("chart-host websocket unavailable");
    }
    const requestId = crypto.randomUUID();
    const frame = {
      type: "webui_request",
      request_id: requestId,
      action: "trading.chart_host_submit",
      payload: { captureId, frames },
    };
    await new Promise<void>((resolve, reject) => {
      const timer = window.setTimeout(() => {
        socket.removeEventListener("message", onMessage);
        reject(new Error("chart-host submit timeout"));
      }, 30_000);
      const onMessage = (event: MessageEvent<string>) => {
        try {
          const payload = JSON.parse(event.data) as {
            event?: string;
            request_id?: string;
            ok?: boolean;
            error?: { message?: string };
          };
          if (payload.event !== "webui_response" || payload.request_id !== requestId) return;
          window.clearTimeout(timer);
          socket.removeEventListener("message", onMessage);
          if (payload.ok) {
            resolve();
            return;
          }
          reject(new Error(payload.error?.message ?? "chart-host submit failed"));
        } catch {
          // Ignore unrelated frames.
        }
      };
      socket.addEventListener("message", onMessage);
      socket.send(JSON.stringify(frame));
    });
  }
}
