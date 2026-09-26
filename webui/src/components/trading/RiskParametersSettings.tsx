import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetchTradingRisk, updateTradingRisk } from "@/lib/api";
import type { TradingRiskField, TradingRiskPayload, TradingRiskToggle } from "@/lib/types";
import { useClient } from "@/providers/ClientProvider";
import { useCallback, useEffect, useMemo, useState } from "react";

function formatTemplate(template: string, vars: Record<string, string>): string {
  let out = template;
  for (const [key, value] of Object.entries(vars)) {
    out = out.replaceAll(`{${key}}`, value);
  }
  return out;
}

export function RiskParametersSettings() {
  const { client, token } = useClient();
  const [payload, setPayload] = useState<TradingRiskPayload | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [toggleDraft, setToggleDraft] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const applyPayload = useCallback((next: TradingRiskPayload) => {
    if (!Array.isArray(next.groups)) {
      throw new Error("Invalid trading risk payload");
    }
    setPayload(next);
    const values: Record<string, string> = {};
    for (const group of next.groups) {
      for (const field of group.fields) {
        values[field.name] = String(field.value);
      }
    }
    setDraft(values);
    const toggles: Record<string, boolean> = {};
    for (const toggle of next.toggles ?? []) {
      toggles[toggle.name] = toggle.enabled;
    }
    setToggleDraft(toggles);
  }, []);

  const refresh = useCallback(async () => {
    const next = await fetchTradingRisk(token);
    applyPayload(next);
  }, [applyPayload, token]);

  useEffect(() => {
    void refresh().catch((err: Error) => setError(err.message));
  }, [refresh]);

  const dirty = useMemo(() => {
    if (!payload) return false;
    const fieldsDirty = payload.groups.some((group) =>
      group.fields.some((field) => draft[field.name] !== String(field.value)),
    );
    const togglesDirty = (payload.toggles ?? []).some(
      (toggle) => toggleDraft[toggle.name] !== toggle.enabled,
    );
    return fieldsDirty || togglesDirty;
  }, [draft, payload, toggleDraft]);

  const save = useCallback(async () => {
    if (!payload) return;
    const values: Record<string, number> = {};
    for (const group of payload.groups) {
      for (const field of group.fields) {
        const raw = (draft[field.name] ?? "").trim();
        const parsed = field.type === "integer" ? Number.parseInt(raw, 10) : Number.parseFloat(raw);
        if (!Number.isFinite(parsed)) {
          setError(formatTemplate(payload.number_required ?? "{field}", { field: field.label }));
          return;
        }
        values[field.name] = parsed;
      }
    }
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const next = await updateTradingRisk(client, values, toggleDraft);
      applyPayload(next);
      setStatus(next.last_action?.message ?? next.save_label);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }, [applyPayload, client, draft, payload, toggleDraft]);

  if (!payload) {
    return (
      <section className="rounded-xl border bg-card p-5" aria-busy="true">
        {error ? <p className="text-sm text-destructive">{error}</p> : <div className="h-6 w-40 animate-pulse rounded bg-muted" />}
      </section>
    );
  }

  return (
    <section className="rounded-xl border bg-card p-5">
      <header className="mb-4">
        <h2 className="font-semibold">{payload.title}</h2>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{payload.description}</p>
      </header>
      <div
        role="note"
        className="mb-5 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3.5 py-3 text-sm text-amber-950 dark:text-amber-100"
      >
        {payload.operator_warning}
      </div>
      {error ? <p className="mb-4 text-sm text-destructive">{error}</p> : null}
      {status ? <p className="mb-4 text-sm text-emerald-600 dark:text-emerald-400">{status}</p> : null}
      {(payload.toggles ?? []).length > 0 ? (
        <div className="mb-6">
          <h3 className="mb-1 text-sm font-medium">{payload.toggles_title}</h3>
          <p className="mb-3 max-w-3xl text-xs text-muted-foreground">
            {payload.toggles_help}
          </p>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {(payload.toggles ?? []).map((toggle) => (
              <ToggleInput
                key={toggle.name}
                toggle={toggle}
                enabled={toggleDraft[toggle.name] ?? toggle.enabled}
                onChange={(next) => {
                  setToggleDraft((prev) => ({ ...prev, [toggle.name]: next }));
                  setStatus(null);
                }}
              />
            ))}
          </div>
        </div>
      ) : null}
      <div className="grid gap-6">
        {(payload.groups ?? []).map((group) => (
          <div key={group.id}>
            <h3 className="mb-3 text-sm font-medium">{group.label}</h3>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {group.fields.map((field) => (
                <RiskFieldInput
                  key={field.name}
                  field={field}
                  value={draft[field.name] ?? ""}
                  minLabel={payload.min_label}
                  maxLabel={payload.max_label}
                  onChange={(next) => {
                    setDraft((prev) => ({ ...prev, [field.name]: next }));
                    setStatus(null);
                  }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
      <Button className="mt-5" onClick={() => void save()} disabled={busy || !dirty}>
        {busy ? payload.saving_label : payload.save_label}
      </Button>
    </section>
  );
}

function ToggleInput({
  toggle,
  enabled,
  onChange,
}: {
  toggle: TradingRiskToggle;
  enabled: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-2 rounded-lg border px-3 py-2 text-sm">
      <input
        type="checkbox"
        className="mt-1"
        checked={enabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span>
        <span className="leading-5 text-foreground">{toggle.label}</span>
        {toggle.never_skips_confirm ? (
          <span className="mt-0.5 block text-xs text-muted-foreground">
            {toggle.confirm_note}
          </span>
        ) : null}
      </span>
    </label>
  );
}

function RiskFieldInput({
  field,
  value,
  onChange,
  minLabel,
  maxLabel,
}: {
  field: TradingRiskField;
  value: string;
  onChange: (value: string) => void;
  minLabel?: string;
  maxLabel?: string;
}) {
  const bounds = [
    field.min !== undefined
      ? formatTemplate(minLabel ?? "{value}", { value: String(field.min) })
      : null,
    field.max !== undefined
      ? formatTemplate(maxLabel ?? "{value}", { value: String(field.max) })
      : null,
    field.unit,
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="leading-5 text-foreground">{field.label}</span>
      <Input
        type="number"
        inputMode="decimal"
        step={field.step}
        min={field.min}
        max={field.max}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <span className="text-xs text-muted-foreground">{bounds}</span>
    </label>
  );
}
