import type { ReactNode } from "react";

export interface AgentCard {
  kind: string;
  [key: string]: unknown;
}

interface AgentCardsProps {
  cards: AgentCard[];
}

function gateStatusLabel(status: string): string {
  if (status === "pass") return "Pass";
  if (status === "veto") return "Veto";
  return "Unavailable";
}

function GateChecklistCard({ card }: { card: AgentCard }) {
  const verdicts = Array.isArray(card.verdicts) ? card.verdicts : [];
  const allowed = card.allowed === true;
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {allowed ? "All required gates passed." : "Recommendation blocked by gates."}
      </p>
      <ul className="space-y-1 text-xs">
        {verdicts.map((row) => {
          if (!row || typeof row !== "object") return null;
          const item = row as Record<string, unknown>;
          const id = String(item.id ?? "");
          const name = String(item.name ?? id);
          const status = String(item.status ?? "");
          const reason = String(item.reason ?? "");
          return (
            <li key={id} className="flex flex-wrap items-baseline gap-x-2">
              <span className="font-medium">{id}</span>
              <span className="text-muted-foreground">{name}</span>
              <span>{gateStatusLabel(status)}</span>
              {reason ? <span className="text-muted-foreground">— {reason}</span> : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function PlanLevelsCard({ card }: { card: AgentCard }) {
  const targets = Array.isArray(card.targets) ? card.targets : [];
  return (
    <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
      <div>
        <span className="text-muted-foreground">Entry</span>
        <div className="font-medium">{String(card.entry ?? "—")}</div>
      </div>
      <div>
        <span className="text-muted-foreground">Stop</span>
        <div className="font-medium">{String(card.stopLoss ?? "—")}</div>
      </div>
      {targets.map((target, index) => (
        <div key={`tp-${index}`}>
          <span className="text-muted-foreground">TP{index + 1}</span>
          <div className="font-medium">{String(target)}</div>
        </div>
      ))}
    </div>
  );
}

function MacroDriversCard({ card }: { card: AgentCard }) {
  const drivers = Array.isArray(card.drivers) ? card.drivers : [];
  return (
    <ul className="space-y-1 text-xs">
      {drivers.map((driver, index) => {
        if (!driver || typeof driver !== "object") return null;
        const item = driver as Record<string, unknown>;
        const name = String(item.name ?? `driver-${index}`);
        if (item.ran === false) {
          return (
            <li key={`${name}-${index}`} className="text-muted-foreground">
              <span className="font-medium">{name}</span> — skipped
            </li>
          );
        }
        const rationale = String(item.one_line_rationale ?? "");
        return (
          <li key={`${name}-${index}`}>
            <span className="font-medium">{name}</span>
            {": "}
            {String(item.bias ?? "neutral")}
            {item.strength != null ? ` (${String(item.strength)})` : ""}
            {rationale ? ` — ${rationale}` : ""}
          </li>
        );
      })}
    </ul>
  );
}

function renderCardBody(card: AgentCard): ReactNode {
  switch (card.kind) {
    case "decision":
      return (
        <div className="space-y-1">
          <div className="text-base font-semibold uppercase">{String(card.decision ?? "")}</div>
          <p className="text-sm text-muted-foreground">{String(card.summary ?? "")}</p>
          {card.confidence != null ? (
            <p className="text-xs text-muted-foreground">
              Confidence {Math.round(Number(card.confidence) * 100)}%
            </p>
          ) : null}
        </div>
      );
    case "plan_levels":
      return <PlanLevelsCard card={card} />;
    case "activation":
      return (
        <p className="text-xs text-muted-foreground">
          Plan: {String(card.planType ?? "immediate")} · State:{" "}
          {String(card.executionState ?? "valid_now")}
        </p>
      );
    case "invalidation":
      return <p className="text-xs">{String(card.summary ?? "")}</p>;
    case "gate_checklist":
      return <GateChecklistCard card={card} />;
    case "visual_review":
      return (
        <div className="space-y-1 text-xs">
          <p>
            Visual state: <span className="font-medium">{String(card.state ?? "not_checked")}</span>
          </p>
          {card.notes ? <p className="text-muted-foreground">{String(card.notes)}</p> : null}
        </div>
      );
    case "macro_drivers":
      return <MacroDriversCard card={card} />;
    case "key_reasons": {
      const reasons = Array.isArray(card.reasons) ? card.reasons : [];
      return (
        <ul className="list-disc space-y-1 pl-4 text-xs">
          {reasons.map((reason, index) => (
            <li key={`reason-${index}`}>{String(reason)}</li>
          ))}
        </ul>
      );
    }
    case "risk_warnings": {
      const warnings = Array.isArray(card.warnings) ? card.warnings : [];
      return (
        <ul className="list-disc space-y-1 pl-4 text-xs text-amber-700 dark:text-amber-300">
          {warnings.map((warning, index) => (
            <li key={`warning-${index}`}>{String(warning)}</li>
          ))}
        </ul>
      );
    }
    case "tracked_recommendation":
      return (
        <p className="text-xs text-muted-foreground">
          Tracking {String(card.direction ?? "").toUpperCase()} on {String(card.symbol ?? "XAUUSD")}{" "}
          ({String(card.interval ?? "")}) — {String(card.status ?? "")}
        </p>
      );
    default:
      return (
        <pre className="whitespace-pre-wrap break-words text-xs text-muted-foreground">
          {JSON.stringify(card, null, 2)}
        </pre>
      );
  }
}

export function AgentCards({ cards }: AgentCardsProps) {
  if (!cards.length) {
    return (
      <p className="text-sm text-muted-foreground">No recommendation cards yet.</p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {cards.map((card, index) => (
        <article
          key={`${card.kind}-${index}`}
          className="rounded-lg border bg-card p-4 text-sm shadow-sm"
        >
          <header className="mb-2 font-medium capitalize">
            {card.kind.replace(/_/g, " ")}
          </header>
          {renderCardBody(card)}
        </article>
      ))}
    </div>
  );
}
