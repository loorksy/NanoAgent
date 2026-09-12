import { ChannelQrConnectFlow } from "@/components/settings/channels/ChannelQrConnectFlow";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  configureChannel,
  enableNanobotFeature,
  fetchNanobotFeatures,
} from "@/lib/api";
import type { NanobotFeatureInfo, NanobotFeaturesPayload } from "@/lib/types";
import { useClient } from "@/providers/ClientProvider";
import { MessageCircle, Send } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

export function TradingConnect() {
  const { client, token } = useClient();
  const [features, setFeatures] = useState<NanobotFeaturesPayload | null>(null);
  const [telegramToken, setTelegramToken] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const payload = await fetchNanobotFeatures(token);
    setFeatures(payload);
  }, [token]);

  useEffect(() => {
    void refresh().catch((err: Error) => setError(err.message));
    const timer = window.setInterval(() => void refresh().catch(() => undefined), 8_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const telegram = features?.features.find((row) => row.name === "telegram");
  const whatsapp = features?.features.find((row) => row.name === "whatsapp");

  const saveTelegram = useCallback(async () => {
    const value = telegramToken.trim();
    if (!value) {
      setError("Paste the Telegram bot token from @BotFather.");
      return;
    }
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      if (telegram && !telegram.installed && telegram.install_supported) {
        await enableNanobotFeature(client, "telegram", { installOnly: true });
      }
      await configureChannel(
        client,
        "telegram",
        { "channels.telegram.token": value },
        { enable: true },
      );
      setTelegramToken("");
      setStatus("Telegram token saved and the channel is enabled.");
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }, [client, refresh, telegram, telegramToken]);

  return (
    <div className="flex h-full flex-col overflow-auto p-4 sm:p-6">
      <header className="mb-6">
        <h1 className="text-lg font-semibold">Connect Telegram & WhatsApp</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Paste the Telegram bot token from @BotFather, or scan the WhatsApp QR.
          This is the only setup screen you need — no extra install step.
        </p>
      </header>

      {error ? <p className="mb-4 text-sm text-destructive">{error}</p> : null}
      {status ? <p className="mb-4 text-sm text-emerald-600 dark:text-emerald-400">{status}</p> : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border bg-card p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#229ED9]/15 text-[#229ED9]">
              <Send className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-semibold">Telegram</h2>
              <p className="text-xs text-muted-foreground">{channelState(telegram)}</p>
            </div>
          </div>
          <ol className="mb-4 list-decimal space-y-1 pl-5 text-sm text-muted-foreground">
            <li>Open Telegram and talk to @BotFather</li>
            <li>Create a bot and copy the token</li>
            <li>Paste it below and save</li>
          </ol>
          <Input
            type="password"
            autoComplete="off"
            placeholder="123456:ABC-DEF..."
            value={telegramToken}
            onChange={(event) => setTelegramToken(event.target.value)}
          />
          <Button className="mt-3" onClick={() => void saveTelegram()} disabled={busy}>
            {busy ? "Saving…" : "Save Telegram token"}
          </Button>
        </section>

        <section className="rounded-xl border bg-card p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#25D366]/15 text-[#25D366]">
              <MessageCircle className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-semibold">WhatsApp</h2>
              <p className="text-xs text-muted-foreground">{channelState(whatsapp)}</p>
            </div>
          </div>
          {whatsapp ? (
            <ChannelQrConnectFlow
              token={token}
              channelName="whatsapp"
              idleLabel="Show WhatsApp QR"
              autoStart
              minimalPending
              forceOnRepeat
              labels={{
                qrAlt: "WhatsApp linking QR code",
                scanTitle: "Link WhatsApp",
                scanDescription:
                  "In WhatsApp, open Linked devices, choose Link a device, then scan this code.",
                waiting: "Waiting for WhatsApp…",
                connected: "WhatsApp is connected.",
                stopped: "The WhatsApp connection attempt stopped. Start again to get a new code.",
                connecting: "Connecting…",
                scanAgain: "Link another account",
                connect: "Link WhatsApp",
              }}
              onFeaturesUpdate={setFeatures}
            />
          ) : (
            <p className="text-sm text-muted-foreground">Loading WhatsApp connector…</p>
          )}
        </section>
      </div>
    </div>
  );
}

function channelState(feature: NanobotFeatureInfo | undefined): string {
  if (!feature) return "Loading…";
  if (feature.running) return "Connected and running";
  if (feature.enabled && feature.configured) return "Enabled — starting";
  if (feature.configured) return "Configured — not enabled";
  return "Not connected";
}
