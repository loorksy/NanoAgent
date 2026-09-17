import { cleanup, render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, vi } from "vitest";
import { SettingsView } from "@/components/settings/SettingsView";
import { ClientProvider } from "@/providers/ClientProvider";
import type { SettingsPayload, TradingMetaApiPayload } from "@/lib/types";

export const requestMutationMock = vi.fn();

export function jsonResponse(body: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => body,
  } as Response;
}

export function tradingMetaApiPayload(
  overrides: Partial<TradingMetaApiPayload> = {},
): TradingMetaApiPayload {
  return {
    title: "Connect MT5 account",
    description: "Link a MetaAPI token and MT5 account from this page.",
    hitl_note: "Orders still require confirm after the account is saved.",
    token_label: "MetaAPI token",
    token_help: "Create a token at app.metaapi.cloud.",
    token_placeholder: "Paste token",
    token_configured_placeholder: "Token saved — paste a new one to replace it",
    account_id_label: "Account ID",
    account_id_help: "Leave empty to provision from login, password, and server.",
    region_label: "Region",
    login_label: "MT5 login",
    password_label: "MT5 password",
    server_label: "Broker server",
    server_placeholder: "Broker-Demo",
    connect_label: "Connect MT5",
    test_label: "Test connection",
    disconnect_label: "Disconnect",
    saving_label: "Saving…",
    testing_label: "Testing…",
    not_connected_label: "Not connected",
    connected_label: "Connected",
    env_override_warning: "Environment variables override this form.",
    sdk_missing_label: "MetaAPI SDK is not installed.",
    steps: ["Create a MetaAPI token", "Enter MT5 login details", "Connect and test"],
    regions: [{ id: "new-york", label: "new-york" }],
    configured: false,
    token_set: false,
    token_hint: null,
    account_id: "",
    region: "new-york",
    sdk_available: true,
    env_override: false,
    source: "none",
    ...overrides,
  };
}

export function settingsPayload(): SettingsPayload {
  return {
    agent: {
      model: "openai/gpt-4o",
      provider: "auto",
      resolved_provider: "openai",
      has_api_key: true,
      model_preset: "primary",
      max_tokens: 8192,
      context_window_tokens: 200000,
      temperature: 0.1,
      reasoning_effort: null,
      timezone: "UTC",
      tool_hint_max_length: 40,
    },
    model_presets: [{
      name: "primary",
      label: "Primary",
      active: true,
      is_default: false,
      model: "openai/gpt-4o",
      provider: "auto",
      resolved_provider: "openai",
      max_tokens: 8192,
      context_window_tokens: 200000,
      temperature: 0.1,
      reasoning_effort: null,
    }],
    model_call_order: ["primary"],
    model_call_order_editable: true,
    providers: [],
    web_search: {
      provider: "duckduckgo",
      api_key_hint: null,
      base_url: null,
      max_results: 5,
      timeout: 30,
      providers: [{ name: "duckduckgo", label: "DuckDuckGo", credential: "none" }],
    },
    web: {
      enable: true,
      proxy: null,
      user_agent: null,
      search: { max_results: 5, timeout: 30 },
      fetch: { use_jina_reader: true },
    },
    api: {
      host: "127.0.0.1",
      port: 8900,
      timeout: 120,
      api_key_hint: null,
    },
    observability: {
      provider: "langfuse",
      configured: false,
      base_url: "https://cloud.langfuse.com",
    },
    image_generation: {
      enabled: false,
      provider: "openrouter",
      provider_configured: false,
      model: "openai/gpt-5.4-image-2",
      default_aspect_ratio: "1:1",
      default_image_size: "1K",
      max_images_per_turn: 4,
      save_dir: "generated",
      providers: [],
    },
    runtime: {
      config_path: "/tmp/config.json",
      workspace_path: "/tmp/workspace",
      gateway_host: "127.0.0.1",
      gateway_port: 18790,
      heartbeat: {
        enabled: true,
        interval_s: 1800,
      },
      dream: {
        schedule: "every 2h",
      },
      unified_session: false,
    },
    advanced: {
      restrict_to_workspace: false,
      webui_allow_local_service_access: true,
      webui_default_access_mode: "default",
      private_service_protection_enabled: true,
      ssrf_whitelist_count: 0,
      mcp_server_count: 0,
      exec_enabled: true,
      exec_sandbox: null,
      exec_path_prepend_set: false,
      exec_path_append_set: false,
    },
    requires_restart: false,
    version: {
      current: "0.2.2",
    },
    docs: {
      version: "0.2.2",
      base_url: "https://nanobot.wiki/docs/0.2.2",
      chat_apps_url: "https://nanobot.wiki/docs/0.2.2/getting-started/chat-apps",
      latest_url: "https://nanobot.wiki/docs/latest",
    },
  };
}

export function renderSettingsView(
  options: {
    initialSection?:
      | "overview"
      | "appearance"
      | "apps"
      | "skills"
      | "channels"
      | "automations"
      | "advanced"
      | "models"
      | "image"
      | "browser"
      | "runtime";
    initialSettings?: SettingsPayload;
    showSidebar?: boolean;
    onBackToChat?: () => void;
    onSettingsChange?: (payload: SettingsPayload) => void;
    onNativeEngineRestart?: () => Promise<string>;
    onRestart?: () => void;
  } = {},
) {
  render(
    <ClientProvider client={{ requestMutation: requestMutationMock } as never} token="tok">
      <SettingsView
        theme="light"
        initialSection={options.initialSection ?? "apps"}
        initialSettings={options.initialSettings}
        showSidebar={options.showSidebar}
        onToggleTheme={() => {}}
        onBackToChat={options.onBackToChat ?? (() => {})}
        onModelNameChange={() => {}}
        onSettingsChange={options.onSettingsChange}
        onNativeEngineRestart={options.onNativeEngineRestart}
        onRestart={options.onRestart}
      />
    </ClientProvider>,
  );
}

export async function openPopover(trigger: HTMLElement) {
  await userEvent.setup().click(trigger);
}

export function installSettingsViewTestHooks() {
  beforeEach(() => {
    requestMutationMock.mockReset().mockResolvedValue(settingsPayload());
    vi.stubGlobal(
      "matchMedia",
      vi.fn((query: string) => ({
        matches: query === "(min-width: 1280px)",
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    );
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>(() => {})),
    );
  });

  afterEach(() => {
    cleanup();
    localStorage.removeItem("nanobot-webui.settings-preferences");
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });
}
