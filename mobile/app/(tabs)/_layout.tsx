import { Link, Tabs } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { useInbox, useT } from "../../src/lib/app-context";
import { colors, font, spacing } from "../../src/lib/theme";
import { unreadCount } from "../../src/stores/notifications";

const ICONS: Record<string, string> = {
  index: "◎",
  tasks: "☰",
  recommendations: "◆",
  connect: "⏻",
  log: "≣",
};

function TabIcon({ name, color }: { name: string; color: string }) {
  return <Text style={{ color, fontSize: 18 }}>{ICONS[name] ?? "•"}</Text>;
}

function HeaderButtons() {
  const unread = useInbox((state) => unreadCount(state.items));
  const t = useT();
  return (
    <View style={styles.headerButtons}>
      <Link href="/notifications" asChild>
        <Pressable accessibilityRole="button" accessibilityLabel={t("notifications.title")} style={styles.headerButton}>
          <Text style={styles.headerIcon}>🔔</Text>
          {unread > 0 ? (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{unread > 99 ? "99+" : unread}</Text>
            </View>
          ) : null}
        </Pressable>
      </Link>
      <Link href="/settings" asChild>
        <Pressable accessibilityRole="button" accessibilityLabel={t("settings.title")} style={styles.headerButton}>
          <Text style={styles.headerIcon}>⚙︎</Text>
        </Pressable>
      </Link>
    </View>
  );
}

export default function TabsLayout() {
  const t = useT();
  return (
    <Tabs
      screenOptions={({ route }) => ({
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.text,
        headerRight: () => <HeaderButtons />,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarIcon: ({ color }) => <TabIcon name={route.name} color={color} />,
        sceneStyle: { backgroundColor: colors.bg },
      })}
    >
      <Tabs.Screen name="index" options={{ title: t("tabs.agent") }} />
      <Tabs.Screen name="tasks" options={{ title: t("tabs.tasks") }} />
      <Tabs.Screen name="recommendations" options={{ title: t("tabs.recommendations") }} />
      <Tabs.Screen name="connect" options={{ title: t("tabs.connect") }} />
      <Tabs.Screen name="log" options={{ title: t("tabs.log") }} />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  headerButtons: { flexDirection: "row", gap: spacing.xs, paddingHorizontal: spacing.sm },
  headerButton: { padding: spacing.sm, position: "relative" },
  headerIcon: { color: colors.text, fontSize: 18 },
  badge: {
    position: "absolute",
    top: 2,
    right: 2,
    backgroundColor: colors.danger,
    borderRadius: 999,
    minWidth: 16,
    height: 16,
    paddingHorizontal: 3,
    alignItems: "center",
    justifyContent: "center",
  },
  badgeText: { color: "#fff", fontSize: font.xs - 1, fontWeight: "700" },
});
