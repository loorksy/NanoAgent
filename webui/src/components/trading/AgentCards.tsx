import type { ReactNode } from "react";
import { cardKindTitle, cardStrings } from "@/lib/trading/cardLocale";
import { displayGateName } from "@/lib/trading/gate-labels";

export interface AgentCard {
  kind: string;
  [key: string]: unknown;
}

interface AgentCardsProps {
  cards: AgentCard[];
  locale?: string | null;
}

function gateStatusLabel(status: string, locale?: string | null): string {
  const t = cardStrings(locale);
  if (status === "pass") return t.pass;
  if (status === "veto") return t.veto;
  return t.unavailable;
}

function GateChecklistCard({ card, locale }: { card: AgentCard; locale?: string | null }) {
  const t = cardStrings(locale);
  const verdicts = Array.isArray(card.verdicts) ? card.verdicts : [];
  const allowed = card.allowed === true;
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {allowed ? t.gatesPass : t.gatesBlock}
      </p>
      <ul className="space-y-1 text-xs">
        {verdicts.map((row) => {
          if (!row || typeof row !== "object") return null;
          const item = row as Record<string, unknown>;
          const id = String(item.id ?? "");
          const label = displayGateName(item, locale);
          const status = String(item.status ?? "");
          const reason = String(item.reason ?? "");
          return (
            <li key={id || label} className="flex flex-wrap items-baseline gap-x-2">
              {label ? <span className="font-medium">{label}</span> : null}
              <span>{gateStatusLabel(status, locale)}</span>
              {reason ? <span className="text-muted-foreground">— {reason}</span> : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function PlanLevelsCard({ card, locale }: { card: AgentCard; locale?: string | null }) {
  const t = cardStrings(locale);
  const targets = Array.isArray(card.targets) ? card.targets : [];
  return (
    <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
      <div>
        <span className="text-muted-foreground">{t.entry}</span>
        <div className="font-medium">{String(card.entry ?? "—")}</div>
      </div>
      <div>
        <span className="text-muted-foreground">{t.stop}</span>
        <div className="font-medium">{String(card.stopLoss ?? "—")}</div>
      </div>
      {targets.map((target, index) => (
        <div key={`tp-${index}`}>
          <span className="text-muted-foreground">{t.target}{index + 1}</span>
          <div className="font-medium">{String(target)}</div>
        </div>
      ))}
    </div>
  );
}

function MacroDriversCard({ card, locale }: { card: AgentCard; locale?: string | null }) {
  const t = cardStrings(locale);
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
              <span className="font-medium">{name}</span> — {t.skipped}
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

function renderCardBody(card: AgentCard, locale?: string | null): ReactNode {
  const t = cardStrings(locale);
  switch (card.kind) {
    case "decision":
      return (
        <div className="space-y-1">
          <div className="text-base font-semibold uppercase">{String(card.decision ?? "")}</div>
          <p className="text-sm text-muted-foreground">{String(card.summary ?? "")}</p>
          {card.confidence != null ? (
            <p className="text-xs text-muted-foreground">
              {t.confidence} {Math.round(Number(card.confidence) * 100)}%
            </p>
          ) : null}
        </div>
      );
    case "plan_levels":
      return <PlanLevelsCard card={card} locale={locale} />;
    case "activation":
      return (
        <p className="text-xs text-muted-foreground">
          {t.plan}: {String(card.planType ?? "immediate")} · {t.state}:{" "}
          {String(card.executionState ?? "valid_now")}
        </p>
      );
    case "invalidation":
      return <p className="text-xs">{String(card.summary ?? "")}</p>;
    case "gate_checklist":
      return <GateChecklistCard card={card} locale={locale} />;
    case "visual_review":
      return (
        <div className="space-y-1 text-xs">
          <p>
            {t.visualState}: <span className="font-medium">{String(card.state ?? "not_checked")}</span>
          </p>
          {card.notes ? <p className="text-muted-foreground">{String(card.notes)}</p> : null}
        </div>
      );
    case "macro_drivers":
      return <MacroDriversCard card={card} locale={locale} />;
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
          {t.tracking} {String(card.direction ?? "").toUpperCase()} {t.on}{" "}
          {String(card.symbol ?? "XAUUSD")} ({String(card.interval ?? "")}) —{" "}
          {String(card.status ?? "")}
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

export function AgentCards({ cards, locale }: AgentCardsProps) {
  const t = cardStrings(locale);
  if (!cards.length) {
    return <p className="text-sm text-muted-foreground">{t.noCards}</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {cards.map((card, index) => (
        <article
          key={`${card.kind}-${index}`}
          className="rounded-lg border bg-card p-4 text-sm shadow-sm"
        >
          <header className="mb-2 font-medium">
            {cardKindTitle(card.kind, locale)}
          </header>
          {renderCardBody(card, locale)}
        </article>
      ))}
    </div>
  );
}
