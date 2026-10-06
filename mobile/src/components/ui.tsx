import type { ReactNode } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type PressableProps,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useT } from "../lib/app-context";
import { colors, font, radius, spacing } from "../lib/theme";

export function Screen({
  children,
  scroll = true,
  padded = true,
  style,
}: {
  children: ReactNode;
  scroll?: boolean;
  padded?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const insets = useSafeAreaInsets();
  const inner: StyleProp<ViewStyle> = [
    padded && styles.padded,
    { paddingBottom: insets.bottom + spacing.lg },
    style,
  ];
  if (!scroll) return <View style={[styles.screen, inner]}>{children}</View>;
  return (
    <ScrollView style={styles.screen} contentContainerStyle={inner} keyboardShouldPersistTaps="handled">
      {children}
    </ScrollView>
  );
}

export function Card({ children, style, tone }: { children: ReactNode; style?: StyleProp<ViewStyle>; tone?: string }) {
  return <View style={[styles.card, tone ? { borderColor: tone } : null, style]}>{children}</View>;
}

export function CardTitle({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <View style={styles.cardTitleRow}>
      <Text style={styles.cardTitle}>{children}</Text>
      {right}
    </View>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <Text style={styles.sectionTitle}>{children}</Text>;
}

export function Row({ label, value, tone }: { label: string; value: ReactNode; tone?: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      {typeof value === "string" || typeof value === "number" ? (
        <Text style={[styles.rowValue, tone ? { color: tone } : null]}>{value}</Text>
      ) : (
        value
      )}
    </View>
  );
}

export function Muted({ children, style }: { children: ReactNode; style?: StyleProp<TextStyle> }) {
  return <Text style={[styles.muted, style]}>{children}</Text>;
}

export function Body({ children, style }: { children: ReactNode; style?: StyleProp<TextStyle> }) {
  return <Text style={[styles.body, style]}>{children}</Text>;
}

export function Badge({ children, tone = colors.textMuted }: { children: ReactNode; tone?: string }) {
  return (
    <View style={[styles.badge, { borderColor: tone }]}>
      <Text style={[styles.badgeText, { color: tone }]}>{children}</Text>
    </View>
  );
}

export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

export function Button({
  title,
  variant = "primary",
  loading = false,
  disabled,
  style,
  ...props
}: PressableProps & { title: string; variant?: ButtonVariant; loading?: boolean; style?: StyleProp<ViewStyle> }) {
  const isDisabled = disabled || loading;
  return (
    <Pressable
      accessibilityRole="button"
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.button,
        styles[`button_${variant}`],
        isDisabled && styles.buttonDisabled,
        pressed && styles.buttonPressed,
        style,
      ]}
      {...props}
    >
      {loading ? (
        <ActivityIndicator color={variant === "primary" ? colors.accentText : colors.text} />
      ) : (
        <Text style={[styles.buttonText, variant === "primary" && { color: colors.accentText }]}>{title}</Text>
      )}
    </Pressable>
  );
}

export function Loading() {
  const t = useT();
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.accent} />
      <Muted style={{ marginTop: spacing.sm }}>{t("common.loading")}</Muted>
    </View>
  );
}

export function Empty({ text }: { text: string }) {
  return (
    <View style={styles.center}>
      <Muted>{text}</Muted>
    </View>
  );
}

export function ErrorBox({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const t = useT();
  const message = describeError(error, t);
  return (
    <Card tone={colors.danger}>
      <Body style={{ color: colors.danger }}>{message}</Body>
      {onRetry ? <Button title={t("common.retry")} variant="secondary" onPress={onRetry} style={{ marginTop: spacing.sm }} /> : null}
    </Card>
  );
}

export function describeError(error: unknown, t: (key: string) => string): string {
  if (!error) return t("common.error_generic");
  if (typeof error === "object" && "messageKey" in error) {
    const err = error as { messageKey: string; status: number; code: string };
    if (err.status === 401) return t("error.auth");
    if (err.status === 403 && err.messageKey.includes("scope")) {
      return err.messageKey.includes("approve") ? t("error.scope.approve") : t("error.scope.control");
    }
    const translated = t(err.messageKey);
    return translated === err.messageKey ? `${t("error.http")} (${err.code})` : translated;
  }
  if (error instanceof TypeError) return t("error.network");
  return t("common.error_generic");
}

export function Chip({ label, selected, onPress, tone }: { label: string; selected: boolean; onPress: () => void; tone?: string }) {
  const color = tone ?? colors.accent;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={[styles.chip, selected && { backgroundColor: color, borderColor: color }]}
    >
      <Text style={[styles.chipText, selected && { color: colors.accentText }]}>{label}</Text>
    </Pressable>
  );
}

export const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  padded: { padding: spacing.lg, gap: spacing.md },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.lg,
    gap: spacing.sm,
  },
  cardTitleRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: spacing.sm },
  cardTitle: { color: colors.text, fontSize: font.lg, fontWeight: "600" },
  sectionTitle: {
    color: colors.textMuted,
    fontSize: font.sm,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.6,
    marginTop: spacing.sm,
  },
  row: { flexDirection: "row", justifyContent: "space-between", gap: spacing.md, paddingVertical: 2 },
  rowLabel: { color: colors.textMuted, fontSize: font.md, flexShrink: 1 },
  rowValue: { color: colors.text, fontSize: font.md, fontWeight: "500", textAlign: "right", flexShrink: 1 },
  muted: { color: colors.textMuted, fontSize: font.sm },
  body: { color: colors.text, fontSize: font.md, lineHeight: 22 },
  badge: {
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    alignSelf: "flex-start",
  },
  badgeText: { fontSize: font.xs, fontWeight: "600", textTransform: "uppercase" },
  button: {
    minHeight: 44,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
  },
  button_primary: { backgroundColor: colors.accent },
  button_secondary: { backgroundColor: colors.surfaceRaised, borderWidth: 1, borderColor: colors.border },
  button_danger: { backgroundColor: colors.danger },
  button_ghost: { backgroundColor: "transparent" },
  buttonDisabled: { opacity: 0.5 },
  buttonPressed: { opacity: 0.8 },
  buttonText: { color: colors.text, fontSize: font.md, fontWeight: "600" },
  center: { alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.sm },
  chip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs + 2,
    backgroundColor: colors.surfaceRaised,
  },
  chipText: { color: colors.text, fontSize: font.sm, fontWeight: "500" },
});
