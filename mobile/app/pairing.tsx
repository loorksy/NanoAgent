import { GatewayClient } from "@nanoagent/sdk";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as Device from "expo-device";
import { useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { Platform, StyleSheet, Text, TextInput, View } from "react-native";

import { Body, Button, Card, Muted, Screen, describeError } from "../src/components/ui";
import { useAuth, useStores, useT } from "../src/lib/app-context";
import { isPairingCode, normalizeGatewayUrl, parseDeepLink } from "../src/lib/deeplink";
import { colors, font, radius, spacing } from "../src/lib/theme";

type Mode = "scan" | "manual";

export default function PairingScreen() {
  const t = useT();
  const params = useLocalSearchParams<{ url?: string; code?: string }>();
  const { auth } = useStores();
  const locale = useAuth((state) => state.locale);
  const [mode, setMode] = useState<Mode>(Platform.OS === "web" ? "manual" : "scan");
  const [url, setUrl] = useState(params.url ?? "");
  const [code, setCode] = useState(params.code ?? "");
  const [label, setLabel] = useState(Device.deviceName ?? Device.modelName ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);
  const scanned = useRef(false);
  const [permission, requestPermission] = useCameraPermissions();

  const pair = useCallback(
    async (gatewayInput: string, pairingCode: string) => {
      const gateway = normalizeGatewayUrl(gatewayInput);
      if (!gateway) {
        setError(t("pairing.invalid_url"));
        return;
      }
      if (!isPairingCode(pairingCode)) {
        setError(t("pairing.invalid_qr"));
        return;
      }
      setBusy(true);
      setError(undefined);
      try {
        const client = new GatewayClient({ baseUrl: gateway, locale });
        const response = await client.pairDevice({ code: pairingCode.trim(), label: label.trim(), locale });
        await auth.getState().pair(gateway, response);
      } catch (err) {
        setError(`${t("pairing.failed")}: ${describeError(err, t)}`);
        scanned.current = false;
      } finally {
        setBusy(false);
      }
    },
    [auth, label, locale, t],
  );

  useEffect(() => {
    if (params.url && params.code && !busy) void pair(params.url, params.code);
    // Only auto-pair once from the deep link.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.url, params.code]);

  const onScan = ({ data }: { data: string }) => {
    if (scanned.current || busy) return;
    const link = parseDeepLink(data);
    if (!link || link.kind !== "pair") {
      setError(t("pairing.invalid_qr"));
      return;
    }
    scanned.current = true;
    setUrl(link.url);
    setCode(link.code);
    void pair(link.url, link.code);
  };

  return (
    <Screen>
      <Text style={styles.title}>{t("pairing.title")}</Text>
      <Body>{t("pairing.intro")}</Body>
      <View style={styles.modes}>
        {Platform.OS !== "web" ? (
          <Button title={t("pairing.scan")} variant={mode === "scan" ? "primary" : "secondary"} onPress={() => setMode("scan")} style={styles.mode} />
        ) : null}
        <Button title={t("pairing.manual")} variant={mode === "manual" ? "primary" : "secondary"} onPress={() => setMode("manual")} style={styles.mode} />
      </View>

      {mode === "scan" ? (
        <Card style={styles.scanner}>
          {permission?.granted ? (
            <>
              <CameraView
                style={styles.camera}
                facing="back"
                barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
                onBarcodeScanned={onScan}
              />
              <Muted style={{ textAlign: "center" }}>{t("pairing.scanning")}</Muted>
            </>
          ) : (
            <>
              <Body>{t("pairing.camera_permission")}</Body>
              <Button title={t("pairing.grant_camera")} onPress={() => void requestPermission()} />
            </>
          )}
        </Card>
      ) : (
        <Card>
          <Muted>{t("pairing.gateway_url")}</Muted>
          <TextInput
            style={styles.input}
            value={url}
            onChangeText={setUrl}
            placeholder={t("pairing.gateway_url_placeholder")}
            placeholderTextColor={colors.textMuted}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            accessibilityLabel={t("pairing.gateway_url")}
          />
          <Muted>{t("pairing.code")}</Muted>
          <TextInput
            style={styles.input}
            value={code}
            onChangeText={setCode}
            keyboardType="number-pad"
            maxLength={10}
            accessibilityLabel={t("pairing.code")}
          />
          <Muted>{t("pairing.device_name")}</Muted>
          <TextInput style={styles.input} value={label} onChangeText={setLabel} accessibilityLabel={t("pairing.device_name")} />
          <Button title={t("pairing.pair")} loading={busy} disabled={!url || !code} onPress={() => void pair(url, code)} />
        </Card>
      )}
      {error ? <Body style={{ color: colors.danger }}>{error}</Body> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { color: colors.text, fontSize: font.xl, fontWeight: "700", marginTop: spacing.xl },
  modes: { flexDirection: "row", gap: spacing.sm },
  mode: { flex: 1 },
  scanner: { alignItems: "stretch" },
  camera: { height: 280, borderRadius: radius.md, overflow: "hidden" },
  input: {
    color: colors.text,
    fontSize: font.md,
    backgroundColor: colors.bg,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
});
