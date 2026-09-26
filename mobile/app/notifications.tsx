import { useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Badge, Button, Chip, Empty, describeError } from "../src/components/ui";
import { useDecide } from "../src/lib/approve";
import { useClient, useInbox, useLabel, useLocale, useStores, useT } from "../src/lib/app-context";
import { parseDeepLink, routeFor } from "../src/lib/deeplink";
import { formatRelative } from "../src/lib/format";
import { colors, font, radius, spacing } from "../src/lib/theme";
import { unreadCount, type InboxItem } from "../src/stores/notifications";

type Filter = "all" | "unread" | "approval";

function levelTone(level: InboxItem["level"]): string {
  if (level === "error") return colors.danger;
  if (level === "warning") return colors.warning;
  return colors.info;
}

function InboxRow({ item, onOpen, onDecide, busy }: { item: InboxItem; onOpen: () => void; onDecide?: (decision: "confirm" | "cancel") => void; busy: boolean }) {
  const t = useT();
  const label = useLabel();
  const locale = useLocale();
  return (
    <Pressable accessibilityRole="button" onPress={onOpen} style={({ pressed }) => [styles.row, !item.read && styles.rowUnread, pressed && styles.rowPressed]}>
      <View style={styles.rowHeader}>
        <Badge tone={levelTone(item.level)}>{t(`notifications.level.${item.level}`)}</Badge>
        <Text style={styles.time}>{formatRelative(item.ts, locale)}</Text>
      </View>
      <Text style={[styles.title, !item.read && styles.titleUnread]}>{label(item.title_key, item.args)}</Text>
      <Text style={styles.body}>{label(item.body_key, item.args)}</Text>
      {onDecide ? (
        <View style={styles.actions}>
          <Button title={t("notifications.action.confirm")} loading={busy} onPress={() => onDecide("confirm")} style={styles.action} />
          <Button title={t("notifications.action.cancel")} variant="secondary" disabled={busy} onPress={() => onDecide("cancel")} style={styles.action} />
        </View>
      ) : null}
    </Pressable>
  );
}

export default function NotificationsScreen() {
  const t = useT();
  const router = useRouter();
  const client = useClient();
  const insets = useSafeAreaInsets();
  const { inbox } = useStores();
  const items = useInbox((state) => state.items);
  const [filter, setFilter] = useState<Filter>("all");
  const [busy, setBusy] = useState<string | undefined>(undefined);
  const describe = useCallback((err: unknown) => describeError(err, t), [t]);
  const decide = useDecide(client, describe);
  const unread = unreadCount(items);

  const visible = useMemo(() => {
    if (filter === "unread") return items.filter((item) => !item.read);
    if (filter === "approval") return items.filter((item) => item.kind === "approval");
    return items;
  }, [items, filter]);

  const open = (item: InboxItem) => {
    void inbox.getState().markRead(item.id);
    const parsed = item.deep_link ? parseDeepLink(item.deep_link) : undefined;
    if (parsed) router.push(routeFor(parsed));
    else if (item.approval_id) router.push(routeFor({ kind: "approval", id: item.approval_id }));
    else if (item.session) router.push(routeFor({ kind: "session", id: item.session }));
  };

  const onDecide = async (item: InboxItem, decision: "confirm" | "cancel") => {
    if (!item.approval_id) return;
    setBusy(item.id);
    try {
      const response = await decide(item.approval_id, decision);
      if (response) await inbox.getState().markRead(item.id);
    } finally {
      setBusy(undefined);
    }
  };

  return (
    <View style={styles.screen}>
      <View style={styles.toolbar}>
        <View style={styles.filters}>
          <Chip label={t("log.filter.all")} selected={filter === "all"} onPress={() => setFilter("all")} />
          <Chip label={t("notifications.unread", { count: unread })} selected={filter === "unread"} onPress={() => setFilter("unread")} />
          <Chip label={t("card.approval.title")} selected={filter === "approval"} onPress={() => setFilter("approval")} />
        </View>
        <View style={styles.toolbarActions}>
          <Button title={t("notifications.mark_read")} variant="ghost" disabled={unread === 0} onPress={() => void inbox.getState().markAllRead()} />
          <Button title={t("notifications.clear")} variant="ghost" disabled={items.length === 0} onPress={() => void inbox.getState().clear()} />
        </View>
      </View>
      <FlatList
        data={visible}
        keyExtractor={(item) => item.id}
        contentContainerStyle={[styles.list, { paddingBottom: insets.bottom + spacing.lg }]}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        ListEmptyComponent={<Empty text={t("notifications.empty")} />}
        renderItem={({ item }) => (
          <InboxRow
            item={item}
            busy={busy === item.id}
            onOpen={() => open(item)}
            {...(item.kind === "approval" && item.approval_id && !item.read && client ? { onDecide: (decision: "confirm" | "cancel") => void onDecide(item, decision) } : {})}
          />
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  toolbar: { padding: spacing.lg, paddingBottom: spacing.sm, gap: spacing.sm },
  filters: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  toolbarActions: { flexDirection: "row", justifyContent: "flex-end", gap: spacing.xs },
  list: { paddingHorizontal: spacing.lg },
  row: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.md,
    gap: spacing.xs,
  },
  rowUnread: { borderColor: colors.accent },
  rowPressed: { opacity: 0.8 },
  rowHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  time: { color: colors.textMuted, fontSize: font.xs },
  title: { color: colors.text, fontSize: font.md },
  titleUnread: { fontWeight: "600" },
  body: { color: colors.textMuted, fontSize: font.sm },
  actions: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.xs },
  action: { flex: 1 },
  separator: { height: spacing.sm },
});
