import type { TimelineEntry } from "@mokli/sdk";

const UNPROVEN_PHASE = new Set(["thinking", "processing", "tool", "streaming"]);

/** Expanded row: technical name, inputs, and result or error. Absent fields stay out. */
export function timelineDetail(entry: TimelineEntry): string {
  if (entry.kind === "tool") {
    const parts = [entry.name];
    if (entry.arguments) parts.push(entry.arguments);
    if (entry.summary) parts.push(entry.summary);
    return parts.join(" · ");
  }
  if (entry.kind === "retry") return entry.error_kind;
  return entry.summary ?? "";
}

export function workingBadgeCopy(
  phase: string | undefined,
  translate: (key: string) => string,
  lookup: (key: string) => string,
  providerThinking = false,
): { title: string; detail: string } {
  const head = (phase ?? "").split(":")[0] ?? "";
  if (head === "thinking" && providerThinking) {
    const fromCatalog = lookup("phase.thinking");
    const detail = fromCatalog.startsWith("phase.")
      ? translate("state.phase.thinking")
      : fromCatalog;
    return { title: translate("state.working"), detail };
  }
  if (head === "" || UNPROVEN_PHASE.has(head)) {
    const fromCatalog = lookup("state.processing");
    const title = fromCatalog.startsWith("state.") ? translate("state.processing") : fromCatalog;
    return { title, detail: "" };
  }
  return { title: translate("state.working"), detail: lookup(`phase.${phase}`) };
}
