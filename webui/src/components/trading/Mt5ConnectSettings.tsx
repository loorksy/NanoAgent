import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  disconnectTradingMetaapi,
  fetchTradingMetaapi,
  testTradingMetaapi,
  updateTradingMetaapi,
} from "@/lib/api";
import type { TradingMetaApiPayload } from "@/lib/types";
import { useClient } from "@/providers/ClientProvider";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

function isConnectPayload(value: TradingMetaApiPayload): boolean {
  return Array.isArray(value.steps) && Array.isArray(value.regions);
}

export function Mt5ConnectSettings() {
  const { i18n } = useTranslation();
  const { client, token } = useClient();
  const locale = i18n.language;
  const [payload, setPayload] = useState<TradingMetaApiPayload | null>(null);
  const [tokenDraft, setTokenDraft] = useState("");
  const [accountId, setAccountId] = useState("");
  const [region, setRegion] = useState("new-york");
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [server, setServer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState<"save" | "test" | "disconnect" | null>(null);

  const applyPayload = useCallback((next: TradingMetaApiPayload) => {
    if (!isConnectPayload(next)) {
      throw new Error("Invalid MT5 connect payload");
    }
    setPayload(next);
    setAccountId(next.account_id ?? "");
    setRegion(next.region || "new-york");
    setTokenDraft("");
    setPassword("");
  }, {});

  const refresh = useCallback(async () => {
    const next = await fetchTradingMetaapi(token, locale);
    applyPayload(next);
  }, [applyPayload, locale, token]);

  useEffect(() => {
    void refresh().catch((err: Error) => setError(err.message));
  }, [refresh]);

  const connect = useCallback(async () => {
    setBusy("save");
    setError(null);
    setStatus(null);
    try {
      const next = await updateTradingMetaapi(client, {
        token: tokenDraft.trim() || undefined,
        accountId: accountId.trim() || undefined,
        region,
        login: login.trim() || undefined,
        password: password.trim() || undefined,
        server: server.trim() || undefined,
        locale,
      });
      applyPayload(next);
      setLogin("");
      setServer("");
      setStatus(next.last_action?.message ?? next.connect_label);
      if (next.last_action?.live_error) {
        setError(next.last_action.live_error);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }, [accountId, applyPayload, client, locale, login, password, region, server, tokenDraft]);

  const test = useCallback(async () => {
    setBusy("test");
    setError(null);
    setStatus(null);
    try {
      const next = await testTradingMetaapi(client, locale);
      applyPayload(next);
      setStatus(next.last_action?.message ?? next.test_label);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }, [applyPayload, client, locale]);

  const disconnect = useCallback(async () => {
    setBusy("disconnect");
    setError(null);
    setStatus(null);
    try {
      const next = await disconnectTradingMetaapi(client, locale);
      applyPayload(next);
      setAccountId("");
      setLogin("");
      setServer("");
      setStatus(next.last_action?.message ?? next.disconnect_label);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }, [applyPayload, client, locale]);

  if (!payload) {
    return (
      <section className="rounded-xl border bg-card p-5" aria-busy="true">
        {error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : (
          <div className="h-6 w-48 animate-pulse rounded bg-muted" />
        )}
      </section>
    );
  }

  const linked = payload.configured;
  return (
    <section className="rounded-xl border bg-card p-5">
      <header className="mb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold">{payload.title}</h2>
            <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{payload.description}</p>
          </div>
          <span
            className={
              linked
                ? "rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-300"
                : "rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground"
            }
          >
            {linked ? payload.connected_label : payload.not_connected_label}
          </span>
        </div>
      </header>
      <div
        role="note"
        className="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3.5 py-3 text-sm text-amber-950 dark:text-amber-100"
      >
        {payload.hitl_note}
      </div>
      {payload.env_override ? (
        <p className="mb-4 text-sm text-amber-800 dark:text-amber-200">{payload.env_override_warning}</p>
      ) : null}
      {!payload.sdk_available ? (
        <p className="mb-4 text-sm text-muted-foreground">{payload.sdk_missing_label}</p>
      ) : null}
      <ol className="mb-5 list-decimal space-y-1 pl-5 text-sm text-muted-foreground">
        {(payload.steps ?? []).map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      {error ? <p className="mb-4 text-sm text-destructive">{error}</p> : null}
      {status ? <p className="mb-4 text-sm text-emerald-600 dark:text-emerald-400">{status}</p> : null}
      {payload.account?.summary?.length ? (
        <p className="mb-4 text-sm text-foreground">{payload.account.summary.join(" · ")}</p>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-sm sm:col-span-2">
          <span>{payload.token_label}</span>
          <Input
            type="password"
            autoComplete="off"
            value={tokenDraft}
            placeholder={
              payload.token_set
                ? payload.token_configured_placeholder
                : payload.token_placeholder
            }
            onChange={(event) => setTokenDraft(event.target.value)}
          />
          <span className="text-xs text-muted-foreground">{payload.token_help}</span>
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span>{payload.login_label}</span>
          <Input
            autoComplete="off"
            value={login}
            onChange={(event) => setLogin(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span>{payload.password_label}</span>
          <Input
            type="password"
            autoComplete="off"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm sm:col-span-2">
          <span>{payload.server_label}</span>
          <Input
            autoComplete="off"
            value={server}
            placeholder={payload.server_placeholder}
            onChange={(event) => setServer(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span>{payload.account_id_label}</span>
          <Input
            autoComplete="off"
            value={accountId}
            onChange={(event) => setAccountId(event.target.value)}
          />
          <span className="text-xs text-muted-foreground">{payload.account_id_help}</span>
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span>{payload.region_label}</span>
          <Select value={region} onValueChange={setRegion}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(payload.regions ?? []).map((row) => (
                <SelectItem key={row.id} value={row.id}>
                  {row.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        <Button onClick={() => void connect()} disabled={busy !== null}>
          {busy === "save" ? payload.saving_label : payload.connect_label}
        </Button>
        <Button
          variant="outline"
          onClick={() => void test()}
          disabled={busy !== null || !payload.configured}
        >
          {busy === "test" ? payload.testing_label : payload.test_label}
        </Button>
        <Button
          variant="outline"
          onClick={() => void disconnect()}
          disabled={busy !== null || (!payload.configured && !payload.token_set)}
        >
          {payload.disconnect_label}
        </Button>
      </div>
    </section>
  );
}
