const UNPROVEN_PHASE = new Set(["thinking", "processing", "tool", "streaming"]);

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
