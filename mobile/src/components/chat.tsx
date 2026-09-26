import type { ArtifactEntry, ChatMessage, StateData, TimelineEntry } from "@nanoagent/sdk";
import type { SubscribeStatus } from "@nanoagent/sdk";
import * as Linking from "expo-linking";
import { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

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
  let detail = "";
  if (state.state === "working" && state.phase) {
    detail = label(`phase.${state.phase}`);
  } else if (state.state === "waiting" && state.waiting_for) {
    detail = t(`state.waiting_for.${state.waiting_for.kind}`);
  } else if (state.state === "completed" && state.outcome) {
    detail = t(`state.outcome.${state.outcome}`);
  }
  return (
    <View style={styles.stateRow}>
      <View style={[styles.dot, { backgroundColor: tone }]} />
      <Text style={[styles.stateText, { color: tone }]}>{t(`state.${state.state}`)}</Text>
      {detail ? <Muted>· {detail}</Muted> : null}
      <View style={{ flex: 1 }} />
      {stream && stream !== "open" ? <Muted>{t(`agent.stream.${stream}`)}</Muted> : null}
    </View>
  );
}

export function Timeline({ entries }: { entries: TimelineEntry[] }) {
  const t = useT();
  const label = useLabel();
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  if (entries.length === 0) return null;
  return (
    <View style={styles.timeline}>
      <Pressable onPress={() => setOpen((value) => !value)} accessibilityRole="button">
        <Muted style={{ color: colors.accent }}>{open ? t("timeline.hide") : t("timeline.show", { count: entries.length })}</Muted>
      </Pressable>
      {open
        ? entries.map((entry) => {
            const tone = entry.status === "failed" ? colors.danger : entry.status === "running" ? colors.info : colors.success;
            const name = entry.kind === "tool" ? label(`tool.${entry.name}`) : label(`subagent.${entry.role}`);
            const display = name.startsWith("tool.") || name.startsWith("subagent.") ? (entry.kind === "tool" ? entry.name : entry.role) : name;
            return (
              <View key={entry.id} style={styles.timelineRow}>
                <View style={[styles.dot, { backgroundColor: tone }]} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.timelineName}>
                    {t(`timeline.${entry.kind}`)} · {display}
                  </Text>
                  {entry.summary ? <Muted>{entry.summary}</Muted> : null}
                </View>
                <Muted>
                  {t(`timeline.${entry.status}`)}
                  {entry.kind === "tool" && entry.duration_ms !== undefined ? ` · ${formatDuration(entry.duration_ms, locale)}` : ""}
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
