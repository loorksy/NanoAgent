import type { ResultRecord, StructuredResult, StructuredType } from "@mokli/sdk";

export const STRUCTURED_TYPES: readonly StructuredType[] = [
  "market",
  "analysis",
  "scenarios",
  "risk",
  "decision",
  "approval",
  "plan_status",
  "scorecard",
] as const;

export function isStructuredType(value: unknown): value is StructuredType {
  return typeof value === "string" && (STRUCTURED_TYPES as readonly string[]).includes(value);
}

/**
 * `GET /results/{id}` returns an untyped payload; narrow it to the card union by `type`.
 * Unknown types are passed through so `ResultCard` can render nothing instead of crashing.
 */
export function toStructuredResult(record: ResultRecord): StructuredResult {
  const base = { type: record.type, result_id: record.id, payload: record.payload, ts: record.ts };
  return (record.session ? { ...base, session: record.session } : base) as unknown as StructuredResult;
}
