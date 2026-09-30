import { activityLine, type ArtifactEntry, type ChatMessage, type StateData, type TimelineEntry } from "@mokli/sdk";
import type { SubscribeStatus } from "@mokli/sdk";
import * as Linking from "expo-linking";
import { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { timelineDetail, workingBadgeCopy } from "../lib/activity";
import { useLabel, useLocale, useT } from "../lib/app-context";
import { formatDuration } from "../lib/format";
import { colors, font, radius, spacing, toneColor, type StateTone } from "../lib/theme";
import { Badge, Button, Muted } from "./ui";

export function stateTone(state: StateData): StateTone {
  if (state.state === "working") return "working";
  if (state.state === "waiting") return "waiting";
  return state.outcome === "error" ? "error" : "completed";
}

/** Working / Waiting / Completed with the current phase or wait reason. */
export function StateBadge({ state, stream }: { state: StateData; stream?: SubscribeStatus }) {
  const t = useT();
  const label = useLabel();
  const tone = toneColor(stateTone(state));
  let title = t(`state.${state.state}`);
  let detail = "";
  if (state.state === "working") {
    const copy = workingBadgeCopy(state.phase, t, label, state.provider_thinking === true);
    title = copy.title;
    detail = copy.detail;
  } else if (state.state === "waiting" && state.waiting_for) {
    detail = t(`state.waiting_for.${state.waiting_for.kind}`);
  } else if (state.state === "completed" && state.outcome) {
    detail = t(`state.outcome.${state.outcome}`);
  }
  return (
    <View style={styles.stateRow}>
      <View style={[styles.dot, { backgroundColor: tone }]} />
      <Text style={[styles.stateText, { color: tone }]}>{title}</Text>
      {detail ? <Muted>· {detail}</Muted> : null}
      <View style={{ flex: 1 }} />
      {stream && stream !== "open" ? <Muted>{t(`agent.stream.${stream}`)}</Muted> : null}
    </View>
  );
}

function isHumanRole(role: string): boolean {
  return Boolean(role) && !role.includes("_") && !(/^[\u0000-\u007f]*$/.test(role) && role === role.toLowerCase());
}

function stepDisplay(
  entry: TimelineEntry,
  translate: (key: string) => string,
  lookup: (key: string) => string,
): string {
  if (entry.kind === "tool") {
    if (entry.display) return entry.display;
    const named = lookup(`tool.${entry.name}`);
    return named.startsWith("tool.") ? translate("timeline.step") : named;
  }
  if (entry.kind === "subagent") {
    if (entry.display) return entry.display;
    const named = lookup(`subagent.${entry.role}`);
    if (!named.startsWith("subagent.")) return named;
    return isHumanRole(entry.role) ? entry.role : translate("timeline.specialist");
  }
  return translate(`retry.${entry.state}`);
}

export function Timeline({ entries }: { entries: TimelineEntry[] }) {
  const t = useT();
  const label = useLabel();
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  if (entries.length === 0) return null;
  const line = activityLine(entries, (entry) => stepDisplay(entry, t, label));
  return (
    <View style={styles.timeline}>
      {line ? <Text style={styles.timelineName}>{line}</Text> : null}
      <Pressable onPress={() => setOpen((value) => !value)} accessibilityRole="button">
        <Muted style={{ color: colors.accent }}>{open ? t("timeline.hide") : t("timeline.show", { count: entries.length })}</Muted>
      </Pressable>
      {open
        ? entries.map((entry) => {
            const tone = entry.status === "failed" ? colors.danger : entry.status === "running" ? colors.info : colors.success;
            const duration = "duration_ms" in entry ? entry.duration_ms : undefined;
            const detail = timelineDetail(entry);
            return (
              <View key={entry.id} style={styles.timelineRow}>
                <View style={[styles.dot, { backgroundColor: tone }]} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.timelineName}>
                    {t(`timeline.${entry.kind}`)} · {stepDisplay(entry, t, label)}
                  </Text>
                  {detail ? <Muted>{detail}</Muted> : null}
                </View>
                <Muted>
                  {t(`timeline.${entry.status}`)}
                  {duration !== undefined ? ` · ${formatDuration(duration, locale)}` : ""}
                </Muted>
              </View>
            );
          })
        : null}
    </View>
  );
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const mine = message.role === "user";
  const imageParts = message.parts?.filter((part) => part.type === "image") ?? [];
  return (
    <View style={[styles.bubble, mine ? styles.bubbleUser : styles.bubbleAgent]}>
      {imageParts.length > 0 ? <Muted>{imageParts.map(() => "🖼").join(" ")}</Muted> : null}
      <Text style={[styles.bubbleText, mine && { color: colors.accentText }]} selectable>
        {message.text || (message.streaming ? "…" : "")}
      </Text>
    </View>
  );
}

export function ArtifactLink({ artifact }: { artifact: ArtifactEntry }) {
  const t = useT();
  return (
    <Pressable onPress={() => void Linking.openURL(artifact.url)} style={styles.artifact} accessibilityRole="link">
      <Badge tone={colors.info}>{artifact.mime.split("/")[0] ?? "file"}</Badge>
      <Text style={styles.artifactText}>{t("artifact.open", { title: artifact.title })}</Text>
    </Pressable>
  );
}

export function Composer({
  onSend,
  onStop,
  working,
  disabled,
}: {
  onSend: (text: string) => Promise<void>;
  onStop: () => Promise<void>;
  working: boolean;
  disabled?: boolean;
}) {
  const t = useT();
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const submit = async () => {
    const value = text.trim();
    if (!value || sending) return;
    setSending(true);
    try {
      await onSend(value);
      setText("");
    } finally {
      setSending(false);
    }
  };
  return (
    <View style={styles.composer}>
      <TextInput
        style={styles.input}
        value={text}
        onChangeText={setText}
        placeholder={t("agent.input_placeholder")}
        placeholderTextColor={colors.textMuted}
        multiline
        editable={!disabled}
        accessibilityLabel={t("agent.input_placeholder")}
      />
      {working ? (
        <Button title={t("agent.stop")} variant="danger" onPress={() => void onStop()} />
      ) : (
        <Button title={t("common.send")} loading={sending} disabled={disabled || !text.trim()} onPress={() => void submit()} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  stateRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingVertical: spacing.xs },
  dot: { width: 8, height: 8, borderRadius: 4 },
  stateText: { fontSize: font.sm, fontWeight: "700", textTransform: "uppercase" },
  timeline: { gap: spacing.xs, paddingVertical: spacing.xs },
  timelineRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingVertical: 2 },
  timelineName: { color: colors.text, fontSize: font.sm },
  bubble: { maxWidth: "88%", borderRadius: radius.lg, padding: spacing.md, marginVertical: spacing.xs },
  bubbleUser: { alignSelf: "flex-end", backgroundColor: colors.accent },
  bubbleAgent: { alignSelf: "flex-start", backgroundColor: colors.surfaceRaised },
  bubbleText: { color: colors.text, fontSize: font.md, lineHeight: 22 },
  artifact: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingVertical: spacing.xs },
  artifactText: { color: colors.info, fontSize: font.sm },
  composer: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: spacing.sm,
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.surface,
  },
  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 140,
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
