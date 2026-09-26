import { LOG_KINDS, type LogEntry, type LogKind } from "@mokli/sdk";
import { useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Badge, Chip, Empty, ErrorBox, Loading, Muted } from "../../src/components/ui";
import { useLabel, useLocale, useRequiredClient, useT } from "../../src/lib/app-context";
import { formatDateTime, toMillis } from "../../src/lib/format";
import { describeLogEntry, logEntryKey, logTone } from "../../src/lib/log";
import { colors, font, radius, spacing } from "../../src/lib/theme";

const PAGE = 100;

function LogRow({ entry, onPress }: { entry: LogEntry; onPress?: () => void }) {
  const t = useT();
  const label = useLabel();
  const locale = useLocale();
  const kindKey = `log.kind.${entry.kind}`;
  const kind = t(kindKey);
  const { title, detail } = describeLogEntry(entry, label);
  return (
    <Pressable accessibilityRole={onPress ? "button" : undefined} disabled={!onPress} onPress={onPress} style={({ pressed }) => [styles.row, pressed && onPress ? styles.rowPressed : null]}>
      <View style={styles.rowHeader}>
        <Badge tone={logTone(entry)}>{kind === kindKey ? entry.kind : kind}</Badge>
        <Muted>{formatDateTime(toMillis(entry.ts), locale)}</Muted>
      </View>
      <Text style={styles.title}>{title}</Text>
      {detail ? <Muted>{detail}</Muted> : null}
      <Muted style={styles.source}>{entry.source}</Muted>
    </Pressable>
  );
}

export default function LogScreen() {
  const t = useT();
  const client = useRequiredClient();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [kinds, setKinds] = useState<LogKind[]>([]);
  const [available, setAvailable] = useState<readonly LogKind[]>(LOG_KINDS);
  const [entries, setEntries] = useState<LogEntry[] | undefined>(undefined);
  const [error, setError] = useState<unknown>(undefined);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const page = await client.getLog({ kinds, limit: PAGE });
      setEntries([...page.entries].sort((a, b) => b.ts - a.ts));
      if (page.kinds.length > 0) setAvailable(page.kinds);
      setError(undefined);
    } catch (err) {
      setError(err);
    } finally {
      setRefreshing(false);
    }
  }, [client, kinds]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggle = (kind: LogKind) => setKinds((current) => (current.includes(kind) ? current.filter((item) => item !== kind) : [...current, kind]));

  const openEntry = (entry: LogEntry) => {
    const data = entry.data;
    if (entry.kind === "structured" && typeof data["result_id"] === "string") {
      router.push(`/result/${encodeURIComponent(data["result_id"])}`);
      return undefined;
    }
    if (entry.kind === "approval" && typeof data["approval_id"] === "string") {
      router.push(`/tasks?approval=${encodeURIComponent(data["approval_id"])}`);
      return undefined;
    }
    if (entry.kind === "job" && typeof data["job_id"] === "string") {
      router.push(`/tasks?job=${encodeURIComponent(data["job_id"])}`);
      return undefined;
    }
    if (typeof data.session === "string" && data.session) {
      router.push(`/?session=${encodeURIComponent(data.session)}`);
    }
    return undefined;
  };

  const linkable = (entry: LogEntry) =>
    (entry.kind === "structured" && typeof entry.data["result_id"] === "string") ||
    (entry.kind === "approval" && typeof entry.data["approval_id"] === "string") ||
    (entry.kind === "job" && typeof entry.data["job_id"] === "string") ||
    (typeof entry.data.session === "string" && Boolean(entry.data.session));

  return (
    <View style={styles.screen}>
      <View style={styles.filters}>
        <Chip label={t("log.filter.all")} selected={kinds.length === 0} onPress={() => setKinds([])} />
        {available.map((kind) => {
          const key = `log.kind.${kind}`;
          const text = t(key);
          return <Chip key={kind} label={text === key ? kind : text} selected={kinds.includes(kind)} onPress={() => toggle(kind)} />;
        })}
      </View>
      {error ? (
        <View style={styles.padded}>
          <ErrorBox error={error} onRetry={() => void load()} />
        </View>
      ) : null}
      {entries === undefined && !error ? <Loading /> : null}
      {entries !== undefined ? (
        <FlatList
          data={entries}
          keyExtractor={logEntryKey}
          renderItem={({ item }) => <LogRow entry={item} onPress={linkable(item) ? () => openEntry(item) : undefined} />}
          contentContainerStyle={[styles.list, { paddingBottom: insets.bottom + spacing.lg }]}
          ItemSeparatorComponent={() => <View style={styles.separator} />}
          ListEmptyComponent={<Empty text={t("log.empty")} />}
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            void load();
          }}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  filters: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, padding: spacing.lg, paddingBottom: spacing.sm },
  padded: { paddingHorizontal: spacing.lg },
  list: { paddingHorizontal: spacing.lg, paddingTop: spacing.sm },
  row: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.md,
    gap: spacing.xs,
  },
  rowPressed: { opacity: 0.8 },
  rowHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: spacing.sm },
  title: { color: colors.text, fontSize: font.md, fontWeight: "500" },
  source: { fontSize: font.xs },
  separator: { height: spacing.sm },
});
