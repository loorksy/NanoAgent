import type { Recommendation } from "@mokli/sdk";
import { useCallback, useEffect, useState } from "react";
import { RefreshControl, ScrollView, StyleSheet } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Badge, Body, Card, CardTitle, Empty, ErrorBox, Loading, Muted, Row, SectionTitle } from "../../src/components/ui";
import { useLocale, useRequiredClient, useT } from "../../src/lib/app-context";
import { formatConfidence, formatDateTime, formatNumber, toMillis } from "../../src/lib/format";
import { colors, spacing } from "../../src/lib/theme";

function directionColor(direction: string): string {
  const lowered = direction.toLowerCase();
  if (lowered.includes("buy") || lowered.includes("long")) return colors.buy;
  if (lowered.includes("sell") || lowered.includes("short")) return colors.sell;
  return colors.wait;
}

function statusColor(status: string): string {
  if (status === "live" || status === "active") return colors.success;
  if (status === "invalidated" || status === "expired") return colors.danger;
  return colors.textMuted;
}

export function RecommendationCard({ item, live = false }: { item: Recommendation; live?: boolean }) {
  const t = useT();
  const locale = useLocale();
  const status = String(item.status);
  const statusLabel = t(`recommendations.status.${status}`);
  return (
    <Card tone={live ? colors.accent : undefined}>
      <CardTitle right={<Badge tone={statusColor(status)}>{statusLabel === `recommendations.status.${status}` ? status : statusLabel}</Badge>}>
        {item.symbol}
        {item.interval ? ` · ${item.interval}` : ""}
      </CardTitle>
      <Badge tone={directionColor(String(item.direction))}>{String(item.direction)}</Badge>
      <Row label={t("recommendations.entry")} value={formatNumber(item.entry, locale, { decimals: 2 })} />
      <Row label={t("recommendations.stop")} value={formatNumber(item.stop_loss, locale, { decimals: 2 })} tone={colors.sell} />
      <Row
        label={t("recommendations.targets")}
        value={item.targets.length ? item.targets.map((target) => formatNumber(target, locale, { decimals: 2 })).join(" · ") : "—"}
        tone={colors.buy}
      />
      <Row label={t("recommendations.confidence")} value={formatConfidence(item.confidence, locale)} />
      {item.summary ? <Body>{item.summary}</Body> : null}
      <Muted>
        {formatDateTime(toMillis(item.created_at), locale)}
        {item.closed_at ? ` → ${formatDateTime(toMillis(item.closed_at), locale)}` : ""}
        {item.close_reason ? ` · ${item.close_reason}` : ""}
      </Muted>
    </Card>
  );
}

export default function RecommendationsScreen() {
  const t = useT();
  const client = useRequiredClient();
  const insets = useSafeAreaInsets();
  const [items, setItems] = useState<Recommendation[] | undefined>(undefined);
  const [error, setError] = useState<unknown>(undefined);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const list = await client.listRecommendations({ limit: 100 });
      setItems(list);
      setError(undefined);
    } catch (err) {
      setError(err);
    } finally {
      setRefreshing(false);
    }
  }, [client]);

  useEffect(() => {
    void load();
  }, [load]);

  const live = (items ?? []).filter((item) => item.status === "live" || item.status === "active");
  const archive = (items ?? []).filter((item) => !live.includes(item));

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
      {items === undefined && !error ? <Loading /> : null}
      <SectionTitle>{t("recommendations.live")}</SectionTitle>
      {items !== undefined && live.length === 0 ? <Empty text={t("recommendations.none_live")} /> : null}
      {live.map((item) => (
        <RecommendationCard key={item.id} item={item} live />
      ))}
      <SectionTitle>{t("recommendations.archive")}</SectionTitle>
      {items !== undefined && archive.length === 0 ? <Empty text={t("recommendations.no_archive")} /> : null}
      {archive.map((item) => (
        <RecommendationCard key={item.id} item={item} />
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg, gap: spacing.md },
});
