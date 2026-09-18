import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Mt5ConnectSettings } from "@/components/trading/Mt5ConnectSettings";
import { ClientProvider } from "@/providers/ClientProvider";
import {
  jsonResponse,
  tradingMetaApiPayload,
} from "@/tests/settings-test-utils";

describe("Mt5ConnectSettings", () => {
  const requestMutation = vi.fn();

  beforeEach(() => {
    requestMutation.mockReset();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.startsWith("/api/settings/trading-metaapi")) {
          return jsonResponse(tradingMetaApiPayload());
        }
        return jsonResponse({});
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function renderForm() {
    return render(
      <ClientProvider
        client={{ requestMutation } as never}
        token="tok"
      >
        <Mt5ConnectSettings />
      </ClientProvider>,
    );
  }

  it("renders the connect form from the settings payload", async () => {
    renderForm();
    expect(await screen.findByText("Connect MT5 account")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Connect MT5" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Test connection" })).toBeDisabled();
  });

  it("does not crash when a settings mock returns an empty object", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({})));
    renderForm();
    expect(await screen.findByText("Invalid MT5 connect payload")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Connect MT5" })).not.toBeInTheDocument();
  });

  it("sends login details through the settings mutation", async () => {
    requestMutation.mockResolvedValue(
      tradingMetaApiPayload({
        configured: true,
        token_set: true,
        account_id: "prov-9",
        last_action: { ok: true, message: "Account linked" },
      }),
    );
    const user = userEvent.setup();
    renderForm();
    await screen.findByText("Connect MT5 account");
    await user.type(screen.getByLabelText("MetaAPI token"), "meta-token");
    await user.type(screen.getByLabelText("MT5 login"), "77001");
    await user.type(screen.getByLabelText("MT5 password"), "broker-pass");
    await user.type(screen.getByLabelText("Broker server"), "Broker-Demo");
    await user.click(screen.getByRole("button", { name: "Connect MT5" }));
    await waitFor(() => {
      expect(requestMutation).toHaveBeenCalledWith(
        "settings.trading_metaapi.update",
        expect.objectContaining({
          token: "meta-token",
          login: "77001",
          password: "broker-pass",
          server: "Broker-Demo",
        }),
        150_000,
      );
    });
    expect(await screen.findByText("Account linked")).toBeInTheDocument();
  });
});
