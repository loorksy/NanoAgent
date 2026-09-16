import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetchTradingRisk, updateTradingRisk } from "@/lib/api";
import type { TradingRiskField, TradingRiskPayload } from "@/lib/types";
import { useClient } from "@/providers/ClientProvider";
import { useCallback, useEffect, useMemo, useState } from "react";

export function RiskParametersSettings() {
  const { client, token } = useClient();
  const [payload, setPayload] = useState<TradingRiskPayload | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const next = await fetchTradingRisk(token);
    setPayload(next);
    const values: Record<string, string> = {};
    for (const group of next.groups) {
      for (const field of group.fields) {
        values[field.name] = String(field.value);
      }
    }
    setDraft(values);
  }, [token]);

  useEffect(() => {
    void refresh().catch((err: Error) => setError(err.message));
  }, [refresh]);

  const dirty = useMemo(() => {
    if (!payload) return false;
    return payload.groups.some((group) =>
      group.fields.some((field) => draft[field.name] !== String(field.value)),
    );
  }, [draft, payload]);

  const save = useCallback(async () => {
    if (!payload) return;
    const values: Record<string, number> = {};
    for (const group of payload.groups) {
      for (const field of group.fields) {
        const raw = (draft[field.name] ?? "").trim();
        const parsed = field.type === "integer" ? Number.parseInt(raw, 10) : Number.parseFloat(raw);
        if (!Number.isFinite(parsed)) {
          setError(`${field.label} must be a number`);
          return;
        }
        values[field.name] = parsed;
      }
    }
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const next = await updateTradingRisk(client, values);
      setPayload(next);
      const nextDraft: Record<string, string> = {};
      for (const group of next.groups) {
        for (const field of group.fields) {
          nextDraft[field.name] = String(field.value);
        }
      }
      setDraft(nextDraft);
      setStatus(next.last_action?.message ?? "Saved.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }, [client, draft, payload]);

  if (!payload) {
    return (
      <section className="rounded-xl border bg-card p-5">
        <h2 className="font-semibold">Risk Parameters</h2>
        <p className="mt-2 text-sm text-muted-foreground">Loading risk parameters…</p>
        {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}
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
      <div className="grid gap-6">
        {payload.groups.map((group) => (
          <div key={group.id}>
            <h3 className="mb-3 text-sm font-medium">{group.label}</h3>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {group.fields.map((field) => (
                <RiskFieldInput
                  key={field.name}
                  field={field}
                  value={draft[field.name] ?? ""}
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
        {busy ? "Saving…" : payload.save_label}
      </Button>
    </section>
  );
}

function RiskFieldInput({
  field,
  value,
  onChange,
}: {
  field: TradingRiskField;
  value: string;
  onChange: (value: string) => void;
}) {
  const bounds = [
    field.min !== undefined ? `min ${field.min}` : null,
    field.max !== undefined ? `max ${field.max}` : null,
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
