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
import { useTranslation } from "react-i18next";

export function TradingConnect() {
  const { t } = useTranslation();
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
      setError(t("trading.connect.tokenRequired"));
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
      setStatus(t("trading.connect.tokenSaved"));
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }, [client, refresh, telegram, telegramToken, t]);

  return (
    <div className="flex h-full flex-col overflow-auto p-4 sm:p-6">
      <header className="mb-6">
        <h1 className="text-lg font-semibold">{t("trading.connect.title")}</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          {t("trading.connect.subtitle")}
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
              <h2 className="font-semibold">{t("trading.connect.telegram")}</h2>
              <p className="text-xs text-muted-foreground">{channelState(telegram, t)}</p>
            </div>
          </div>
          <ol className="mb-4 list-decimal space-y-1 pl-5 text-sm text-muted-foreground">
            <li>{t("trading.connect.telegramSteps.openBotFather")}</li>
            <li>{t("trading.connect.telegramSteps.createBot")}</li>
            <li>{t("trading.connect.telegramSteps.pasteToken")}</li>
          </ol>
          <Input
            type="password"
            autoComplete="off"
            placeholder={t("trading.connect.tokenPlaceholder")}
            value={telegramToken}
            onChange={(event) => setTelegramToken(event.target.value)}
          />
          <Button className="mt-3" onClick={() => void saveTelegram()} disabled={busy}>
            {busy ? t("trading.connect.saving") : t("trading.connect.saveToken")}
          </Button>
        </section>

        <section className="rounded-xl border bg-card p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#25D366]/15 text-[#25D366]">
              <MessageCircle className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-semibold">{t("trading.connect.whatsapp")}</h2>
              <p className="text-xs text-muted-foreground">{channelState(whatsapp, t)}</p>
            </div>
          </div>
          {whatsapp ? (
            <ChannelQrConnectFlow
              token={token}
              channelName="whatsapp"
              idleLabel={t("trading.connect.whatsappQr.idleLabel")}
              autoStart
              minimalPending
              forceOnRepeat
              labels={{
                qrAlt: t("trading.connect.whatsappQr.qrAlt"),
                scanTitle: t("trading.connect.whatsappQr.scanTitle"),
                scanDescription: t("trading.connect.whatsappQr.scanDescription"),
                waiting: t("trading.connect.whatsappQr.waiting"),
                connected: t("trading.connect.whatsappQr.connected"),
                stopped: t("trading.connect.whatsappQr.stopped"),
                connecting: t("trading.connect.whatsappQr.connecting"),
                scanAgain: t("trading.connect.whatsappQr.scanAgain"),
                connect: t("trading.connect.whatsappQr.connect"),
              }}
              onFeaturesUpdate={setFeatures}
            />
          ) : (
            <p className="text-sm text-muted-foreground">{t("trading.connect.loadingWhatsapp")}</p>
          )}
        </section>
      </div>
    </div>
  );
}

function channelState(
  feature: NanobotFeatureInfo | undefined,
  t: (key: string) => string,
): string {
  if (!feature) return t("trading.connect.channelLoading");
  if (feature.running) return t("trading.connect.channelConnectedRunning");
  if (feature.enabled && feature.configured) return t("trading.connect.channelEnabledStarting");
  if (feature.configured) return t("trading.connect.channelConfiguredNotEnabled");
  return t("trading.connect.channelNotConnected");
}
