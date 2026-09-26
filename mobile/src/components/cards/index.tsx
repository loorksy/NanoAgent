/**
 * One component per structured result `type` (07 §5). Each reads the payload directly and
 * resolves every label through the gateway catalog (server → bundled → key).
 */
import type {
  AnalysisPayload,
  ApprovalDecision,
  ApprovalPayload,
  DecisionPayload,
  MarketPayload,
  PlanStatusPayload,
  RiskPayload,
  ScenariosPayload,
  ScorecardPayload,
  StructuredResult,
} from "@mokli/sdk";
import { StyleSheet, Text, View } from "react-native";

import { useLabel, useLocale, useT } from "../../lib/app-context";
import {
  formatConfidence,
  formatDateTime,
  formatNumber,
  formatPercent,
  formatRelative,
  toMillis,
} from "../../lib/format";
import { colors, spacing } from "../../lib/theme";
import { Badge, Body, Button, Card, CardTitle, Muted, Row } from "../ui";

function verdictColor(value: string): string {
  if (value === "buy" || value === "bullish") return colors.buy;
  if (value === "sell" || value === "bearish") return colors.sell;
  return colors.wait;
}

function feedColor(status: string): string {
  if (status === "connected") return colors.success;
  if (status === "degraded") return colors.warning;
  return colors.danger;
}

export function MarketCard({ payload }: { payload: MarketPayload }) {
  const t = useT();
  const locale = useLocale();
  const label = useLabel();
  const next = payload.next_event;
  return (
    <Card>
      <CardTitle right={<Badge tone={feedColor(payload.feed_status)}>{t(`feed.${payload.feed_status}`)}</Badge>}>
        {t("card.market.title")}
      </CardTitle>
      <Text style={styles.price}>{formatNumber(payload.price, locale, { decimals: 2 })}</Text>
      <Row label={t("card.market.spread")} value={formatNumber(payload.spread, locale, { decimals: 2 })} />
      <Row label={t("card.market.session")} value={label(`session.${payload.session}`)} />
      <Row label={t("card.market.dxy")} value={formatNumber(payload.dxy, locale, { decimals: 2 })} />
      <Row label={t("card.market.yields")} value={formatNumber(payload.yields, locale, { decimals: 3 })} />
      {next ? (
        <Row
          label={t("card.market.next_event")}
          value={`${next.title_key ? label(next.title_key) : t(`impact.${next.impact}`)} · ${formatRelative(toMillis(next.time), locale)}`}
          tone={next.impact === "high" ? colors.danger : undefined}
        />
      ) : null}
    </Card>
  );
}

export function AnalysisCard({ payload }: { payload: AnalysisPayload }) {
  const t = useT();
  const locale = useLocale();
  const label = useLabel();
  return (
    <Card>
      <CardTitle right={<Badge tone={verdictColor(payload.htf_bias)}>{t(`bias.${payload.htf_bias}`)}</Badge>}>
        {t("card.analysis.title")}
      </CardTitle>
      <Row label={t("card.analysis.structure")} value={label(payload.structure)} />
      <Row label={t("card.analysis.momentum")} value={formatNumber(payload.momentum_score, locale, { decimals: 2 })} />
      {payload.zones.length > 0 ? (
        <View>
          <Muted>{t("card.analysis.zones")}</Muted>
          {payload.zones.map((zone, index) => (
            <Body key={`zone-${index}`}>
              {formatNumber(zone.low, locale, { decimals: 2 })} – {formatNumber(zone.high, locale, { decimals: 2 })}
              {zone.label_key ? ` · ${label(zone.label_key)}` : ""}
              {zone.timeframe ? ` · ${zone.timeframe}` : ""}
            </Body>
          ))}
        </View>
      ) : null}
      {payload.fvg.length > 0 ? (
        <View>
          <Muted>{t("card.analysis.fvg")}</Muted>
          {payload.fvg.map((gap, index) => (
            <Body key={`fvg-${index}`}>
              {formatNumber(gap.low, locale, { decimals: 2 })} – {formatNumber(gap.high, locale, { decimals: 2 })}
            </Body>
          ))}
        </View>
      ) : null}
      {payload.liquidity.length > 0 ? (
        <View>
          <Muted>{t("card.analysis.liquidity")}</Muted>
          {payload.liquidity.map((level, index) => (
            <Body key={`liq-${index}`} style={{ color: verdictColor(level.side) }}>
              {formatNumber(level.level, locale, { decimals: 2 })} · {t(`direction.${level.side}`)}
              {level.label_key ? ` · ${label(level.label_key)}` : ""}
            </Body>
          ))}
        </View>
      ) : null}
      {payload.confluence.length > 0 ? (
        <View>
          <Muted>{t("card.analysis.confluence")}</Muted>
          {payload.confluence.map((item) => (
            <Body key={item}>• {label(item)}</Body>
          ))}
        </View>
      ) : null}
    </Card>
  );
}

export function ScenariosCard({ payload }: { payload: ScenariosPayload }) {
  const t = useT();
  const label = useLabel();
  const scenarios: [key: "primary" | "alternate", value: ScenariosPayload["primary"]][] = [
    ["primary", payload.primary],
    ["alternate", payload.alternate],
  ];
  return (
    <Card>
      <CardTitle>{t("card.scenarios.title")}</CardTitle>
      {scenarios.map(([key, scenario]) => (
        <View key={key} style={[styles.scenario, payload.active === key && styles.scenarioActive]}>
          <View style={styles.scenarioHeader}>
            <Text style={styles.scenarioName}>{t(`card.scenarios.${key}`)}</Text>
            <Badge tone={verdictColor(scenario.direction)}>{t(`direction.${scenario.direction}`)}</Badge>
            {payload.active === key ? <Badge tone={colors.accent}>{t("card.scenarios.active")}</Badge> : null}
          </View>
          <Row label={t("card.scenarios.trigger")} value={label(scenario.trigger)} />
          <Row label={t("card.scenarios.invalidation")} value={label(scenario.invalidation)} />
        </View>
      ))}
    </Card>
  );
}

export function RiskCard({ payload }: { payload: RiskPayload }) {
  const t = useT();
  const locale = useLocale();
  const label = useLabel();
  return (
    <Card tone={payload.blockers.length > 0 ? colors.warning : undefined}>
      <CardTitle>{t("card.risk.title")}</CardTitle>
      <Row label={t("card.risk.risk_pct")} value={formatPercent(payload.risk_pct, locale, 2)} />
      <Row label={t("card.risk.lot")} value={formatNumber(payload.lot, locale, { decimals: 2 })} />
      <Row label={t("card.risk.rr")} value={t("risk.unit.rr", { value: formatNumber(payload.rr, locale, { decimals: 1 }) })} />
      <Row label={t("card.risk.daily_dd_used")} value={formatPercent(payload.daily_dd_used_pct, locale)} />
      <Row label={t("card.risk.open_positions")} value={formatNumber(payload.open_positions, locale, { decimals: 0 })} />
      <Muted>{t("card.risk.blockers")}</Muted>
      {payload.blockers.length === 0 ? (
        <Body style={{ color: colors.success }}>{t("card.risk.no_blockers")}</Body>
      ) : (
        payload.blockers.map((blocker, index) => (
          <Body key={`${blocker.gate}-${index}`} style={{ color: colors.warning }}>
            • {label(blocker.gate)}: {label(blocker.reason_key)}
          </Body>
        ))
      )}
    </Card>
  );
}

export function DecisionCard({ payload }: { payload: DecisionPayload }) {
  const t = useT();
  const locale = useLocale();
  const label = useLabel();
  const tone = verdictColor(payload.verdict);
  return (
    <Card tone={tone}>
      <CardTitle right={<Badge tone={tone}>{t(`verdict.${payload.verdict}`)}</Badge>}>{t("card.decision.title")}</CardTitle>
      <Row label={t("card.decision.entry")} value={formatNumber(payload.entry, locale, { decimals: 2 })} />
      <Row label={t("card.decision.stop")} value={formatNumber(payload.stop, locale, { decimals: 2 })} tone={colors.sell} />
      <Row
        label={t("card.decision.targets")}
        value={payload.targets.length ? payload.targets.map((target) => formatNumber(target, locale, { decimals: 2 })).join(" · ") : "—"}
        tone={colors.buy}
      />
      <Row label={t("card.decision.confidence")} value={formatConfidence(payload.confidence, locale)} />
      {payload.reasons.length > 0 ? (
        <View>
          <Muted>{t("card.decision.reasons")}</Muted>
          {payload.reasons.map((reason, index) => (
            <Body key={`${reason}-${index}`}>• {label(reason)}</Body>
          ))}
        </View>
      ) : null}
      {payload.gates_passed.length > 0 ? (
        <View style={styles.gates}>
          {payload.gates_passed.map((gate) => (
            <Badge key={gate} tone={colors.success}>
              {label(gate)}
            </Badge>
          ))}
        </View>
      ) : null}
    </Card>
  );
}

export interface ApprovalCardProps {
  payload: ApprovalPayload;
  status?: string;
  busy?: boolean;
  onDecide?: (approvalId: string, decision: ApprovalDecision) => void;
}

export function ApprovalCard({ payload, status = "pending", busy = false, onDecide }: ApprovalCardProps) {
  const t = useT();
  const locale = useLocale();
  const expiresAt = toMillis(payload.expires_at);
  const expired = status === "expired" || (status === "pending" && expiresAt !== null && expiresAt < Date.now());
  const pending = status === "pending" && !expired;
  const actions = payload.actions ?? ["confirm", "cancel"];
  return (
    <Card tone={pending ? colors.warning : undefined}>
      <CardTitle right={<Badge tone={pending ? colors.warning : colors.textMuted}>{t(`approval.status.${expired ? "expired" : status}`)}</Badge>}>
        {t(`approval.type.${payload.type}`)}
      </CardTitle>
      <Body>{payload.summary}</Body>
      <Row label={t("card.approval.permission_level")} value={t(`mt5.level.${payload.permission_level}`)} />
      {expiresAt !== null ? (
        <Muted>{expired ? t("card.approval.expired") : t("card.approval.expires", { when: formatRelative(expiresAt, locale) })}</Muted>
      ) : null}
      {pending && onDecide ? (
        <View style={styles.actions}>
          {actions.includes("confirm") ? (
            <Button title={t("card.approval.confirm")} loading={busy} onPress={() => onDecide(payload.approval_id, "confirm")} style={styles.action} />
          ) : null}
          {actions.includes("cancel") ? (
            <Button
              title={t("card.approval.cancel")}
              variant="danger"
              disabled={busy}
              onPress={() => onDecide(payload.approval_id, "cancel")}
              style={styles.action}
            />
          ) : null}
        </View>
      ) : null}
    </Card>
  );
}

export function PlanStatusCard({ payload }: { payload: PlanStatusPayload }) {
  const t = useT();
  const locale = useLocale();
  const label = useLabel();
  const pnl = payload.pnl ?? null;
  return (
    <Card>
      <CardTitle right={<Badge tone={colors.accent}>{t(`plan.state.${payload.state}`)}</Badge>}>{t("card.plan_status.title")}</CardTitle>
      <Row label={t("card.plan_status.plan")} value={payload.plan_id} />
      {pnl !== null ? (
        <Row label={t("card.plan_status.pnl")} value={formatNumber(pnl, locale, { decimals: 2, signed: true })} tone={pnl >= 0 ? colors.buy : colors.sell} />
      ) : null}
      {payload.transitions.length > 0 ? (
        <View>
          <Muted>{t("card.plan_status.transitions")}</Muted>
          {payload.transitions.map((transition, index) => (
            <Body key={`${transition.ts}-${index}`}>
              {formatDateTime(toMillis(transition.ts), locale)} · {t(`plan.state.${transition.from}`)} → {t(`plan.state.${transition.to}`)}
              {transition.reason_key ? ` · ${label(transition.reason_key)}` : ""}
            </Body>
          ))}
        </View>
      ) : null}
    </Card>
  );
}

export function ScorecardCard({ payload }: { payload: ScorecardPayload }) {
  const t = useT();
  const locale = useLocale();
  const label = useLabel();
  return (
    <Card>
      <CardTitle right={<Muted>{payload.period}</Muted>}>{t("card.scorecard.title")}</CardTitle>
      <Row label={t("card.scorecard.trades")} value={formatNumber(payload.trades, locale, { decimals: 0 })} />
      <Row label={t("card.scorecard.win_rate")} value={formatPercent(payload.win_rate <= 1 ? payload.win_rate * 100 : payload.win_rate, locale)} />
      <Row label={t("card.scorecard.expectancy")} value={formatNumber(payload.expectancy, locale, { decimals: 2, signed: true })} />
      <Row label={t("card.scorecard.max_dd")} value={formatPercent(payload.max_dd, locale)} tone={colors.sell} />
      {payload.notes_keys.length > 0 ? (
        <View>
          <Muted>{t("card.scorecard.notes")}</Muted>
          {payload.notes_keys.map((key) => (
            <Body key={key}>• {label(key)}</Body>
          ))}
        </View>
      ) : null}
    </Card>
  );
}

export interface ResultCardProps {
  result: StructuredResult;
  approvalStatus?: string;
  approvalBusy?: boolean;
  onDecide?: (approvalId: string, decision: ApprovalDecision) => void;
}

/** Dispatch on `type`; unknown types render nothing so a newer gateway never crashes the app. */
export function ResultCard({ result, approvalStatus, approvalBusy, onDecide }: ResultCardProps) {
  switch (result.type) {
    case "market":
      return <MarketCard payload={result.payload} />;
    case "analysis":
      return <AnalysisCard payload={result.payload} />;
    case "scenarios":
      return <ScenariosCard payload={result.payload} />;
    case "risk":
      return <RiskCard payload={result.payload} />;
    case "decision":
      return <DecisionCard payload={result.payload} />;
    case "approval":
      return (
        <ApprovalCard
          payload={result.payload}
          {...(approvalStatus !== undefined ? { status: approvalStatus } : {})}
          {...(approvalBusy !== undefined ? { busy: approvalBusy } : {})}
          {...(onDecide ? { onDecide } : {})}
        />
      );
    case "plan_status":
      return <PlanStatusCard payload={result.payload} />;
    case "scorecard":
      return <ScorecardCard payload={result.payload} />;
    default:
      return null;
  }
}

const styles = StyleSheet.create({
  price: { color: colors.text, fontSize: 32, fontWeight: "700", fontVariant: ["tabular-nums"] },
  scenario: { borderWidth: 1, borderColor: colors.border, borderRadius: 12, padding: spacing.md, gap: spacing.xs },
  scenarioActive: { borderColor: colors.accent },
  scenarioHeader: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.xs },
  scenarioName: { color: colors.text, fontWeight: "600", flex: 1 },
  gates: { flexDirection: "row", flexWrap: "wrap", gap: spacing.xs, marginTop: spacing.xs },
  actions: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm },
  action: { flex: 1 },
});
