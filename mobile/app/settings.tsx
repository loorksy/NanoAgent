import * as Application from "expo-application";
import { useRouter } from "expo-router";
import { useState } from "react";
import { Alert, I18nManager, Platform, StyleSheet, View } from "react-native";

import { Badge, Body, Button, Card, CardTitle, Chip, Muted, Row, Screen, describeError } from "../src/components/ui";
import { LOCALES, isRTL, type Locale } from "../src/i18n";
import { useAuth, useClient, useStores, useT } from "../src/lib/app-context";
import { registerForPush } from "../src/lib/push";
import { colors, spacing } from "../src/lib/theme";

export default function SettingsScreen() {
  const t = useT();
  const router = useRouter();
  const client = useClient();
  const { auth } = useStores();
  const gatewayUrl = useAuth((state) => state.gatewayUrl);
  const token = useAuth((state) => state.token);
  const clientId = useAuth((state) => state.clientId);
  const deviceId = useAuth((state) => state.deviceId);
  const scopes = useAuth((state) => state.scopes);
  const locale = useAuth((state) => state.locale);
  const pushPlatform = useAuth((state) => state.pushPlatform);
  const [pushBusy, setPushBusy] = useState(false);
  const [pushError, setPushError] = useState<string | undefined>(undefined);
  const [restartHint, setRestartHint] = useState(false);

  const changeLocale = async (next: Locale) => {
    if (next === locale) return;
    await auth.getState().setLocale(next);
    if (client) client.locale = next;
    if (I18nManager.isRTL !== isRTL(next)) {
      I18nManager.allowRTL(isRTL(next));
      I18nManager.forceRTL(isRTL(next));
      setRestartHint(true);
    }
  };

  const registerPush = async () => {
    if (!client) return;
    setPushBusy(true);
    setPushError(undefined);
    const result = await registerForPush(client, auth, { label: Platform.OS });
    setPushBusy(false);
    if (!result.ok) {
      setPushError(result.reason === "denied" ? t("settings.push_denied") : result.reason === "unsupported" ? t("settings.push_not_registered") : describeError(result.error, t));
    }
  };

  const unpair = () =>
    Alert.alert(t("settings.unpair"), t("settings.unpair_body"), [
      { text: t("common.cancel"), style: "cancel" },
      {
        text: t("settings.unpair"),
        style: "destructive",
        onPress: () => {
          void (async () => {
            if (client && deviceId) {
              try {
                await client.deleteDevice(deviceId);
              } catch {
                /* the token is removed locally regardless; the operator revokes server-side */
              }
            }
            await auth.getState().unpair();
            router.replace("/pairing");
          })();
        },
      },
    ]);

  return (
    <Screen>
      <Card>
        <CardTitle>{t("settings.gateway_url")}</CardTitle>
        <Body>{gatewayUrl ?? "—"}</Body>
        <Row label={t("settings.token")} value={<Badge tone={token ? colors.success : colors.danger}>{token ? t("settings.token_present") : t("settings.token_missing")}</Badge>} />
        {clientId ? <Row label={t("settings.client_id")} value={clientId} /> : null}
        {deviceId ? <Row label={t("settings.device_id")} value={deviceId} /> : null}
        <View style={styles.chips}>
          {scopes.map((scope) => (
            <Badge key={scope} tone={colors.accent}>
              {scope}
            </Badge>
          ))}
        </View>
      </Card>

      <Card>
        <CardTitle>{t("settings.locale")}</CardTitle>
        <View style={styles.chips}>
          {LOCALES.map((item) => (
            <Chip key={item} label={t(`settings.locale.${item}`)} selected={locale === item} onPress={() => void changeLocale(item)} />
          ))}
        </View>
        {restartHint ? <Muted>{t("settings.rtl_restart")}</Muted> : null}
      </Card>

      <Card>
        <CardTitle right={<Badge tone={pushPlatform ? colors.success : colors.textMuted}>{pushPlatform ? t("settings.push_registered", { platform: pushPlatform }) : t("settings.push_not_registered")}</Badge>}>
          {t("settings.push")}
        </CardTitle>
        <Button title={t("settings.push_register")} variant="secondary" loading={pushBusy} disabled={!client} onPress={() => void registerPush()} />
        {pushError ? <Muted style={{ color: colors.danger }}>{pushError}</Muted> : null}
        <Button title={t("settings.notifications_inbox")} variant="ghost" onPress={() => router.push("/notifications")} />
      </Card>

      <Card>
        <Row label={t("settings.version")} value={`${Application.nativeApplicationVersion ?? "dev"} (${Application.nativeBuildVersion ?? "-"})`} />
      </Card>

      <Button title={t("settings.unpair")} variant="danger" onPress={unpair} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.xs },
});
