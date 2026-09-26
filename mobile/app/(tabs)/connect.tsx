import type {
  ConnectStatus,
  Mt5Permissions,
  Mt5PermissionsPayload,
  Mt5PermissionsUpdate,
  PermissionLevel,
  RiskFieldDescriptor,
  RiskProfileName,
  RiskSettings,
  TradingSession,
} from "@nanoagent/sdk";
import Slider from "@react-native-community/slider";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, RefreshControl, ScrollView, StyleSheet, Switch, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import {
  Badge,
  Body,
  Button,
  Card,
  CardTitle,
  Chip,
  ErrorBox,
  Loading,
  Muted,
  Row,
  SectionTitle,
} from "../../src/components/ui";
import { useAuth, useLabel, useLocale, useRequiredClient, useT } from "../../src/lib/app-context";
import { confirmWithBiometrics } from "../../src/lib/biometric";
import { formatNumber, formatPercent, formatRelative, toMillis } from "../../src/lib/format";
import { MT5_CAPABILITY_FLAGS, PERMISSION_LEVELS, expiryFromHours, formatRiskValue, widensAuthority } from "../../src/lib/risk";
import { colors, spacing } from "../../src/lib/theme";

const POLL_MS = 20_000;
const EXPIRY_CHOICES: readonly { key: "none" | "1d" | "7d" | "30d"; hours: number | null }[] = [
  { key: "1d", hours: 24 },
  { key: "7d", hours: 24 * 7 },
  { key: "30d", hours: 24 * 30 },
  { key: "none", hours: null },
];
const BOOLEAN_FLAGS: readonly (keyof Mt5Permissions)[] = [...MT5_CAPABILITY_FLAGS, "news_lock"];

function RiskSlider({ field, disabled, onCommit }: { field: RiskFieldDescriptor; disabled: boolean; onCommit: (value: number) => void }) {
  const t = useT();
  const locale = useLocale();
  const [draft, setDraft] = useState(field.value);
  useEffect(() => setDraft(field.value), [field.value]);
  const min = field.slider?.min ?? field.min ?? 0;
  const max = field.slider?.max ?? field.max ?? Math.max(field.value * 2, 1);
  const step = field.slider?.step ?? field.step;
  const labelKey = `risk.field.${field.name}`;
  const label = t(labelKey);
  return (
    <View style={styles.slider}>
      <Row label={label === labelKey ? field.label : label} value={formatRiskValue(field, draft, t, locale)} tone={colors.accent} />
      <Slider
        minimumValue={min}
        maximumValue={max}
        step={step}
        value={field.value}
        disabled={disabled}
        minimumTrackTintColor={colors.accent}
        maximumTrackTintColor={colors.border}
        thumbTintColor={colors.accent}
        onValueChange={setDraft}
        onSlidingComplete={(value) => {
          const rounded = field.type === "integer" ? Math.round(value) : Number(value.toFixed(4));
          if (rounded !== field.value) onCommit(rounded);
        }}
      />
      {field.derived ? <Muted>{t("mt5.max_lot_derived")}</Muted> : null}
    </View>
  );
}

function RuntimeCard({
  status,
  saving,
  onKill,
  onPause,
  onPaper,
}: {
  status: ConnectStatus;
  saving: string | undefined;
  onKill: (enabled: boolean) => void;
  onPause: (paused: boolean) => void;
  onPaper: (enabled: boolean) => void;
}) {
  const t = useT();
  const locale = useLocale();
  const canControl = useAuth((state) => state.hasScope("control"));
  const runtime = status.runtime_state;
  const risk = status.risk_state;
  return (
    <Card tone={runtime.kill_switch ? colors.danger : undefined}>
      <CardTitle right={runtime.paper_mode ? <Badge tone={colors.info}>{t("connect.paper_mode")}</Badge> : undefined}>{t("connect.runtime")}</CardTitle>
      {runtime.kill_switch ? <Body style={{ color: colors.danger }}>{t("connect.kill_active")}</Body> : null}
      {runtime.kill_switch ? (
        <Button title={t("connect.release_kill")} variant="secondary" disabled={!canControl} loading={saving === "kill"} onPress={() => onKill(false)} />
      ) : (
        <Button
          title={t("connect.kill_switch")}
          variant="danger"
          disabled={!canControl}
          loading={saving === "kill"}
          onPress={() =>
            Alert.alert(t("connect.kill_confirm_title"), t("connect.kill_confirm_body"), [
              { text: t("common.cancel"), style: "cancel" },
              { text: t("common.confirm"), style: "destructive", onPress: () => onKill(true) },
            ])
          }
        />
      )}
      <View style={styles.toggleRow}>
        <View style={styles.toggleText}>
          <Body>{runtime.paused ? t("connect.resume") : t("connect.pause")}</Body>
          {runtime.paused ? <Muted>{t("connect.paused_hint")}</Muted> : null}
        </View>
        <Switch value={runtime.paused} disabled={!canControl || saving === "pause"} onValueChange={onPause} trackColor={{ true: colors.warning }} />
      </View>
      <View style={styles.toggleRow}>
        <View style={styles.toggleText}>
          <Body>{t("connect.paper_mode")}</Body>
          <Muted>{runtime.paper_mode ? t("connect.paper_hint") : t("connect.live_hint")}</Muted>
        </View>
        <Switch value={runtime.paper_mode} disabled={!canControl || saving === "paper"} onValueChange={onPaper} trackColor={{ true: colors.info }} />
      </View>
      <SectionTitle>{t("connect.risk_state")}</SectionTitle>
      <Row label={t("connect.consecutive_losses")} value={formatNumber(risk.consecutive_losses, locale, { decimals: 0 })} />
      <Row label={t("connect.daily_pnl")} value={formatPercent(risk.daily_pnl_pct, locale, 2)} tone={risk.daily_pnl_pct < 0 ? colors.sell : colors.buy} />
      <Row label={t("card.risk.open_positions")} value={formatNumber(risk.open_positions, locale, { decimals: 0 })} />
      {risk.cooldown_until_ms ? <Muted>{t("connect.cooldown_until", { when: formatRelative(risk.cooldown_until_ms, locale) })}</Muted> : null}
      {risk.emergency_lock ? <Badge tone={colors.danger}>{t("connect.emergency_lock")}</Badge> : null}
      <SectionTitle>{t("connect.brokers")}</SectionTitle>
      <Row
        label={t("connect.oanda")}
        value={
          <Badge tone={status.brokers.oanda.configured ? colors.success : colors.textMuted}>
            {status.brokers.oanda.configured ? `${t("broker.configured")} · ${status.brokers.oanda.env}` : t("broker.unconfigured")}
          </Badge>
        }
      />
      <Row
        label={t("connect.metaapi")}
        value={
          <Badge tone={status.brokers.metaapi["configured"] ? colors.success : colors.textMuted}>
            {status.brokers.metaapi["configured"] ? t("broker.configured") : t("broker.unconfigured")}
          </Badge>
        }
      />
    </Card>
  );
}

function RiskCardEditor({ risk, saving, onProfile, onField }: { risk: RiskSettings; saving: string | undefined; onProfile: (name: RiskProfileName) => void; onField: (name: string, value: number) => void }) {
  const t = useT();
  const canControl = useAuth((state) => state.hasScope("control"));
  const profile = risk.profile.detected ?? risk.profile.name;
  const sliderFields = useMemo(() => {
    const wanted = new Set(risk.profile.slider_fields);
    const all = risk.groups.flatMap((group) => group.fields);
    const chosen = all.filter((field) => wanted.has(field.name));
    return chosen.length > 0 ? chosen : all.filter((field) => field.slider && !field.derived);
  }, [risk]);
  return (
    <Card>
      <CardTitle right={saving === "risk" ? <Muted>{t("connect.saving")}</Muted> : undefined}>{t("connect.risk_profile")}</CardTitle>
      <View style={styles.chips}>
        {risk.profile.presets.map((preset) => (
          <Chip
            key={preset.name}
            label={t(`profile.${preset.name}`)}
            selected={profile === preset.name}
            onPress={() => (canControl ? onProfile(preset.name) : undefined)}
          />
        ))}
        {profile === "custom" ? <Chip label={t("profile.custom")} selected onPress={() => undefined} /> : null}
      </View>
      {risk.description ? <Muted>{risk.description}</Muted> : null}
      {sliderFields.map((field) => (
        <RiskSlider key={field.name} field={field} disabled={!canControl || saving === "risk"} onCommit={(value) => onField(field.name, value)} />
      ))}
    </Card>
  );
}

function Mt5Card({ payload, saving, onSave }: { payload: Mt5PermissionsPayload; saving: string | undefined; onSave: (update: Mt5PermissionsUpdate, requiresBiometric: boolean) => void }) {
  const t = useT();
  const locale = useLocale();
  const label = useLabel();
  const canControl = useAuth((state) => state.hasScope("control"));
  const current = payload.permissions;
  const effective = payload.effective;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Mt5PermissionsUpdate>({});
  const merged: Mt5Permissions = { ...current, ...draft };
  const dirty = Object.keys(draft).length > 0;

  const setLevel = (level: PermissionLevel) => setDraft((state) => ({ ...state, level }));
  const toggle = (flag: keyof Mt5Permissions, value: boolean) => setDraft((state) => ({ ...state, [flag]: value }));
  const toggleSession = (name: TradingSession) => {
    const sessions = merged.sessions.includes(name) ? merged.sessions.filter((item) => item !== name) : [...merged.sessions, name];
    setDraft((state) => ({ ...state, sessions }));
  };
  const setExpiry = (hours: number | null) => setDraft((state) => ({ ...state, expires_at: expiryFromHours(hours) }));

  const levelFromCatalog = (level: PermissionLevel) => {
    const server = payload.levels.find((item) => item.name === level)?.label;
    const local = t(`mt5.level.${level}`);
    return local !== `mt5.level.${level}` ? local : (server ?? level);
  };

  const save = () => {
    onSave(draft, widensAuthority(current, merged));
    setDraft({});
    setEditing(false);
  };

  return (
    <Card tone={merged.level === "execute" ? colors.warning : undefined}>
      <CardTitle
        right={
          canControl ? (
            <Button title={editing ? t("common.cancel") : t("mt5.edit")} variant="ghost" onPress={() => (editing ? (setDraft({}), setEditing(false)) : setEditing(true))} />
          ) : undefined
        }
      >
        {t("connect.mt5_permissions")}
      </CardTitle>
      <View style={styles.chips}>
        {PERMISSION_LEVELS.map((level) => (
          <Chip key={level} label={levelFromCatalog(level)} selected={merged.level === level} onPress={() => (editing ? setLevel(level) : undefined)} tone={level === "execute" ? colors.warning : colors.accent} />
        ))}
      </View>
      <Muted>{t(`mt5.level.${merged.level}_hint`)}</Muted>
      {BOOLEAN_FLAGS.map((flag) => (
        <View key={flag} style={styles.toggleRow}>
          <Body>{t(`mt5.${flag}`)}</Body>
          <Switch value={Boolean(merged[flag])} disabled={!editing || merged.level === "recommend"} onValueChange={(value) => toggle(flag, value)} trackColor={{ true: colors.accent }} />
        </View>
      ))}
      <Row
        label={t("mt5.max_lot")}
        value={effective.max_lot_per_order === null ? t("common.none") : formatNumber(effective.max_lot_per_order, locale, { decimals: 2 })}
      />
      {current.max_lot_per_order === null ? <Muted>{t("mt5.max_lot_derived")}</Muted> : null}
      <SectionTitle>{t("mt5.sessions")}</SectionTitle>
      <View style={styles.chips}>
        {payload.sessions.map((session) => {
          const name = session.name as TradingSession;
          const key = `session.${name}`;
          const text = t(key);
          return (
            <Chip
              key={name}
              label={text === key ? label(key) : text}
              selected={merged.sessions.includes(name)}
              onPress={() => (editing ? toggleSession(name) : undefined)}
            />
          );
        })}
      </View>
      <SectionTitle>{t("mt5.expiry")}</SectionTitle>
      {editing ? (
        <View style={styles.chips}>
          {EXPIRY_CHOICES.map((choice) => (
            <Chip
              key={choice.key}
              label={t(`mt5.expiry.${choice.key}`)}
              selected={"expires_at" in draft ? (choice.hours === null ? draft.expires_at === null : draft.expires_at !== null && Math.abs((draft.expires_at ?? 0) - (expiryFromHours(choice.hours) ?? 0)) < 120) : false}
              onPress={() => setExpiry(choice.hours)}
            />
          ))}
        </View>
      ) : (
        <Muted>{current.expires_at ? t("mt5.expires_at", { when: formatRelative(toMillis(current.expires_at), locale) }) : t("mt5.expiry.none")}</Muted>
      )}
      <Muted>{t("mt5.granted_by", { who: current.granted_by || t("common.unknown") })}</Muted>
      {editing ? <Button title={t("common.save")} disabled={!dirty} loading={saving === "mt5"} onPress={save} /> : null}
    </Card>
  );
}

export default function ConnectScreen() {
  const t = useT();
  const client = useRequiredClient();
  const insets = useSafeAreaInsets();
  const [status, setStatus] = useState<ConnectStatus | undefined>(undefined);
  const [risk, setRisk] = useState<RiskSettings | undefined>(undefined);
  const [mt5, setMt5] = useState<Mt5PermissionsPayload | undefined>(undefined);
  const [error, setError] = useState<unknown>(undefined);
  const [actionError, setActionError] = useState<unknown>(undefined);
  const [saving, setSaving] = useState<string | undefined>(undefined);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [connect, riskSettings, permissions] = await Promise.all([client.getConnect(), client.getRisk(), client.getMt5Permissions()]);
      setStatus(connect);
      setRisk(riskSettings);
      setMt5(permissions);
      setError(undefined);
    } catch (err) {
      setError(err);
    } finally {
      setRefreshing(false);
    }
  }, [client]);

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  const run = async (key: string, action: () => Promise<void>) => {
    setSaving(key);
    setActionError(undefined);
    try {
      await action();
    } catch (err) {
      setActionError(err);
    } finally {
      setSaving(undefined);
    }
  };

  const applyRuntime = (response: { runtime_state: ConnectStatus["runtime_state"] }) =>
    setStatus((current) => (current ? { ...current, runtime_state: response.runtime_state } : current));

  const onSaveMt5 = async (update: Mt5PermissionsUpdate, requiresBiometric: boolean) => {
    if (requiresBiometric) {
      const gate = await confirmWithBiometrics(t("biometric.prompt"));
      if (!gate.ok) {
        if (gate.reason === "unavailable") Alert.alert(t("biometric.unavailable"));
        else if (gate.reason === "failed") Alert.alert(t("biometric.failed"));
        return;
      }
    }
    await run("mt5", async () => {
      const response = await client.setMt5Permissions(update, "mobile");
      setMt5(response);
      Alert.alert(t("mt5.saved"));
    });
  };

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + spacing.lg }]}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          tintColor={colors.accent}
          onRefresh={() => {
            setRefreshing(true);
            void load();
          }}
        />
      }
    >
      {error ? <ErrorBox error={error} onRetry={() => void load()} /> : null}
      {actionError ? <ErrorBox error={actionError} /> : null}
      {!status && !error ? <Loading /> : null}
      {status ? (
        <RuntimeCard
          status={status}
          saving={saving}
          onKill={(enabled) => void run("kill", async () => applyRuntime(await client.kill(enabled)))}
          onPause={(paused) => void run("pause", async () => applyRuntime(await client.pause(paused)))}
          onPaper={(enabled) => void run("paper", async () => applyRuntime(await client.setPaperMode(enabled)))}
        />
      ) : null}
      {risk ? (
        <RiskCardEditor
          risk={risk}
          saving={saving}
          onProfile={(name) => void run("risk", async () => setRisk(await client.setRiskProfile(name)))}
          onField={(name, value) => void run("risk", async () => setRisk(await client.setRiskField(name, value)))}
        />
      ) : null}
      {mt5 ? <Mt5Card payload={mt5} saving={saving} onSave={(update, biometric) => void onSaveMt5(update, biometric)} /> : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg, gap: spacing.md },
  toggleRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: spacing.md, paddingVertical: spacing.xs },
  toggleText: { flex: 1, gap: 2 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  slider: { gap: 2, paddingTop: spacing.xs },
});
