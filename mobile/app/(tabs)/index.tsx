import { setApprovalStatus, type ApprovalDecision, type ArtifactEntry, type ChatMessage, type Session, type StructuredResult } from "@nanoagent/sdk";
import { useSession } from "@nanoagent/sdk/react";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FlatList, KeyboardAvoidingView, Modal, Platform, Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ResultCard } from "../../src/components/cards";
import { ArtifactLink, Composer, MessageBubble, StateBadge, Timeline } from "../../src/components/chat";
import { Button, Card, Empty, ErrorBox, Muted, describeError } from "../../src/components/ui";
import { useDecide } from "../../src/lib/approve";
import { useLocale, useRequiredClient, useStores, useT } from "../../src/lib/app-context";
import { formatRelative } from "../../src/lib/format";
import { colors, font, radius, spacing } from "../../src/lib/theme";

type Item =
  | { key: string; kind: "message"; message: ChatMessage }
  | { key: string; kind: "result"; result: StructuredResult }
  | { key: string; kind: "artifact"; artifact: ArtifactEntry };

export default function AgentScreen() {
  const t = useT();
  const locale = useLocale();
  const router = useRouter();
  const client = useRequiredClient();
  const { labels, inbox } = useStores();
  const params = useLocalSearchParams<{ session?: string }>();
  const insets = useSafeAreaInsets();

  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>(params.session);
  const [drawer, setDrawer] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(undefined);
  const [busyApproval, setBusyApproval] = useState<string | undefined>(undefined);

  const controller = useSession(client, sessionId);
  const { snapshot, status, error, send, cancel, store } = controller;
  const describe = useCallback((err: unknown) => describeError(err, t), [t]);
  const decide = useDecide(client, describe);

  useEffect(() => {
    void labels.getState().load(client, locale);
  }, [client, labels, locale]);

  const refreshSessions = useCallback(async () => {
    try {
      const list = await client.listSessions();
      setSessions(list);
      setLoadError(undefined);
      if (!sessionId && list[0]) setSessionId(list[0].id);
    } catch (err) {
      setLoadError(err);
    }
  }, [client, sessionId]);

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions]);

  useEffect(() => {
    if (params.session) setSessionId(params.session);
  }, [params.session]);

  // Mirror pending approvals into the inbox: the gateway suppresses push while this device is live.
  const lastSeen = useRef<string | undefined>(undefined);
  useEffect(() => {
    const pending = snapshot.approvals.filter((item) => item.status === "pending");
    const latest = pending[pending.length - 1];
    if (latest && latest.approval_id !== lastSeen.current) {
      lastSeen.current = latest.approval_id;
      void inbox.getState().addEvent({
        id: `evt-${latest.approval_id}`,
        session: snapshot.sessionId,
        ts: latest.ts,
        kind: "approval",
        data: { approval_id: latest.approval_id, type: latest.type, summary: latest.summary, expires_at: latest.expires_at, status: "pending" },
      });
    }
  }, [snapshot.approvals, snapshot.sessionId, inbox]);

  const newSession = async () => {
    try {
      const created = await client.createSession({});
      setSessions((list) => [created, ...list]);
      setSessionId(created.id);
      setDrawer(false);
    } catch (err) {
      setLoadError(err);
    }
  };

  const onDecide = async (approvalId: string, decision: ApprovalDecision) => {
    setBusyApproval(approvalId);
    try {
      const response = await decide(approvalId, decision);
      if (response) store.update((current) => setApprovalStatus(current, approvalId, response.status));
    } finally {
      setBusyApproval(undefined);
    }
  };

  const items = useMemo<Item[]>(() => {
    const merged: { ts: number; item: Item }[] = [];
    for (const message of snapshot.messages) merged.push({ ts: message.ts, item: { key: `m-${message.id}`, kind: "message", message } });
    for (const result of snapshot.results) merged.push({ ts: result.ts ?? 0, item: { key: `r-${result.result_id}`, kind: "result", result } });
    for (const artifact of snapshot.artifacts) merged.push({ ts: artifact.ts, item: { key: `a-${artifact.id}`, kind: "artifact", artifact } });
    merged.sort((a, b) => a.ts - b.ts);
    return merged.map((entry) => entry.item);
  }, [snapshot.messages, snapshot.results, snapshot.artifacts]);

  const approvalStatus = (result: StructuredResult): string | undefined => {
    if (result.type !== "approval") return undefined;
    return snapshot.approvals.find((item) => item.approval_id === result.payload.approval_id)?.status ?? "pending";
  };

  const working = snapshot.state.state === "working";
  const currentTitle = sessions.find((session) => session.id === sessionId)?.title || t("agent.untitled");

  return (
    <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={insets.top + 56}>
      <View style={styles.topBar}>
        <Pressable onPress={() => setDrawer(true)} style={styles.sessionButton} accessibilityRole="button" accessibilityLabel={t("agent.sessions")}>
          <Text style={styles.sessionTitle} numberOfLines={1}>
            {sessionId ? currentTitle : t("agent.select_session")}
          </Text>
          <Text style={styles.chevron}>▾</Text>
        </Pressable>
        <Button title="+" variant="secondary" onPress={() => void newSession()} style={styles.newButton} />
      </View>
      {sessionId ? (
        <View style={styles.stateBar}>
          <StateBadge state={snapshot.state} stream={status} />
          <Timeline entries={snapshot.timeline} />
        </View>
      ) : null}
      {loadError ? (
        <View style={{ padding: spacing.lg }}>
          <ErrorBox error={loadError} onRetry={() => void refreshSessions()} />
        </View>
      ) : null}
      {error ? (
        <View style={{ paddingHorizontal: spacing.lg }}>
          <Muted style={{ color: colors.danger }}>{describe(error)}</Muted>
        </View>
      ) : null}

      {!sessionId ? (
        <View style={styles.emptyWrap}>
          <Empty text={t("agent.no_sessions")} />
          <Button title={t("agent.new_session")} onPress={() => void newSession()} />
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.key}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<Empty text={t("agent.no_messages")} />}
          renderItem={({ item }) => {
            if (item.kind === "message") return <MessageBubble message={item.message} />;
            if (item.kind === "artifact") return <ArtifactLink artifact={item.artifact} />;
            const status = approvalStatus(item.result);
            return (
              <View style={{ marginVertical: spacing.xs }}>
                <ResultCard
                  result={item.result}
                  {...(status !== undefined ? { approvalStatus: status } : {})}
                  approvalBusy={item.result.type === "approval" && busyApproval === item.result.payload.approval_id}
                  onDecide={(id, decision) => void onDecide(id, decision)}
                />
              </View>
            );
          }}
        />
      )}

      {sessionId ? <Composer onSend={send} onStop={cancel} working={working} /> : null}

      <Modal visible={drawer} animationType="slide" transparent onRequestClose={() => setDrawer(false)}>
        <Pressable style={styles.backdrop} onPress={() => setDrawer(false)} />
        <View style={[styles.drawer, { paddingTop: insets.top + spacing.lg }]}>
          <View style={styles.drawerHeader}>
            <Text style={styles.drawerTitle}>{t("agent.sessions")}</Text>
            <Button title={t("agent.new_session")} variant="secondary" onPress={() => void newSession()} />
          </View>
          <FlatList
            data={sessions}
            keyExtractor={(session) => session.id}
            ListEmptyComponent={<Empty text={t("agent.no_sessions")} />}
            renderItem={({ item }) => (
              <Pressable
                onPress={() => {
                  setSessionId(item.id);
                  setDrawer(false);
                  router.setParams({ session: item.id });
                }}
                style={[styles.sessionRow, item.id === sessionId && styles.sessionRowActive]}
              >
                <View style={{ flex: 1 }}>
                  <Text style={styles.sessionRowTitle} numberOfLines={1}>
                    {item.title || t("agent.untitled")}
                  </Text>
                  <Muted>{formatRelative(item.updated_at || item.created_at, locale)}</Muted>
                </View>
                {item.state && item.state !== "completed" ? <Muted style={{ color: colors.info }}>{t(`state.${item.state}`)}</Muted> : null}
              </Pressable>
            )}
          />
          <Card>
            <Button
              title={t("agent.delete_session")}
              variant="danger"
              disabled={!sessionId}
              onPress={async () => {
                if (!sessionId) return;
                await client.deleteSession(sessionId).catch(setLoadError);
                setSessions((list) => list.filter((session) => session.id !== sessionId));
                setSessionId(undefined);
                setDrawer(false);
              }}
            />
          </Card>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  sessionButton: { flex: 1, flexDirection: "row", alignItems: "center", gap: spacing.xs },
  sessionTitle: { color: colors.text, fontSize: font.md, fontWeight: "600", flexShrink: 1 },
  chevron: { color: colors.textMuted },
  newButton: { minHeight: 36, paddingHorizontal: spacing.md },
  stateBar: { paddingHorizontal: spacing.lg, paddingVertical: spacing.xs },
  list: { padding: spacing.lg, gap: spacing.xs },
  emptyWrap: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.md },
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)" },
  drawer: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    maxHeight: "80%",
    padding: spacing.lg,
    gap: spacing.md,
  },
  drawerHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  drawerTitle: { color: colors.text, fontSize: font.lg, fontWeight: "700" },
  sessionRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingVertical: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.border },
  sessionRowActive: { borderBottomColor: colors.accent },
  sessionRowTitle: { color: colors.text, fontSize: font.md },
});
