import type { ApprovalDecision, ResultRecord } from "@mokli/sdk";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { ResultCard } from "../../src/components/cards";
import { Badge, Button, Card, CardTitle, Empty, ErrorBox, Loading, Muted, Row, Screen, describeError } from "../../src/components/ui";
import { useDecide } from "../../src/lib/approve";
import { useLocale, useRequiredClient, useT } from "../../src/lib/app-context";
import { formatDateTime, toMillis } from "../../src/lib/format";
import { toStructuredResult } from "../../src/lib/results";
import { colors, font, spacing } from "../../src/lib/theme";

export default function ResultScreen() {
  const t = useT();
  const locale = useLocale();
  const router = useRouter();
  const client = useRequiredClient();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [record, setRecord] = useState<ResultRecord | undefined>(undefined);
  const [error, setError] = useState<unknown>(undefined);
  const [notFound, setNotFound] = useState(false);
  const [approvalStatus, setApprovalStatus] = useState<string | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const describe = useCallback((err: unknown) => describeError(err, t), [t]);
  const decide = useDecide(client, describe);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const fetched = await client.getResult(id);
      setRecord(fetched);
      setNotFound(false);
      setError(undefined);
      if (fetched.type === "approval" && typeof fetched.payload["approval_id"] === "string") {
        try {
          const approval = await client.getApproval(fetched.payload["approval_id"]);
          setApprovalStatus(approval.status);
        } catch {
          /* approval may be purged while the result record remains */
        }
      }
    } catch (err) {
      if (typeof err === "object" && err !== null && "status" in err && (err as { status: number }).status === 404) setNotFound(true);
      else setError(err);
    }
  }, [client, id]);

  useEffect(() => {
    void load();
  }, [load]);

  const onDecide = async (approvalId: string, decision: ApprovalDecision) => {
    setBusy(true);
    try {
      const response = await decide(approvalId, decision);
      if (response) setApprovalStatus(response.status);
    } finally {
      setBusy(false);
    }
  };

  if (notFound) return <Screen><Empty text={t("result.not_found")} /></Screen>;
  if (error) return <Screen><ErrorBox error={error} onRetry={() => void load()} /></Screen>;
  if (!record) return <Screen><Loading /></Screen>;

  const typeKey = `card.${record.type}.title`;
  const typeLabel = t(typeKey);
  return (
    <Screen>
      <Card>
        <CardTitle right={<Badge tone={colors.accent}>{typeLabel === typeKey ? record.type : typeLabel}</Badge>}>{t("result.title")}</CardTitle>
        <Row label="ID" value={record.id} />
        <Muted>{formatDateTime(toMillis(record.ts), locale)}</Muted>
        {record.session ? (
          <Button title={t("result.open_session")} variant="ghost" onPress={() => router.push(`/?session=${encodeURIComponent(record.session ?? "")}`)} />
        ) : null}
      </Card>
      <ResultCard
        result={toStructuredResult(record)}
        {...(approvalStatus !== undefined ? { approvalStatus } : {})}
        approvalBusy={busy}
        onDecide={(approvalId, decision) => void onDecide(approvalId, decision)}
      />
      <Button title={showRaw ? t("result.hide_raw") : t("result.show_raw")} variant="ghost" onPress={() => setShowRaw((value) => !value)} />
      {showRaw ? (
        <View style={styles.raw}>
          <Text selectable style={styles.rawText}>
            {JSON.stringify(record.payload, null, 2)}
          </Text>
        </View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  raw: { backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: 12, padding: spacing.md },
  rawText: { color: colors.textMuted, fontSize: font.xs, fontFamily: "monospace" },
});
