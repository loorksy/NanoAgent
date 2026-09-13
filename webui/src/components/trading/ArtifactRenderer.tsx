import { cardStrings } from "@/lib/trading/cardLocale";
import { gateLabel } from "@/lib/trading/gate-labels";
import { useTranslation } from "react-i18next";

export interface TradingArtifact {
  type: string;
  title?: string;
  mime?: string;
  payload?: Record<string, unknown>;
}

interface ArtifactRendererProps {
  artifacts: TradingArtifact[];
  locale?: string | null;
}

function ChartSnapshotArtifact({
  artifact,
}: {
  artifact: TradingArtifact;
}) {
  const { t } = useTranslation();
  const payload = artifact.payload ?? {};
  const src = String(payload.image ?? "");
  if (!src) {
    return <p className="text-xs text-muted-foreground">{t("trading.chart.noChartImage")}</p>;
  }
  return (
    <img
      src={src.startsWith("data:") ? src : src}
      alt={artifact.title ?? t("trading.chart.chartSnapshotAlt")}
      className="max-h-80 w-full rounded-md border object-contain"
    />
  );
}

function LevelMapArtifact({
  artifact,
  locale,
}: {
  artifact: TradingArtifact;
  locale?: string | null;
}) {
  const t = cardStrings(locale);
  const payload = artifact.payload ?? {};
  const targets = Array.isArray(payload.targets) ? payload.targets : [];
  return (
    <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
      <div>
        <span className="text-muted-foreground">{t.entry}</span>
        <div className="font-medium">{String(payload.entry ?? "—")}</div>
      </div>
      <div>
        <span className="text-muted-foreground">{t.stop}</span>
        <div className="font-medium">{String(payload.stopLoss ?? "—")}</div>
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

function GateReportArtifact({
  artifact,
  locale,
}: {
  artifact: TradingArtifact;
  locale?: string | null;
}) {
  const t = cardStrings(locale);
  const payload = artifact.payload ?? {};
  const verdicts = Array.isArray(payload.verdicts) ? payload.verdicts : [];
  const allowed = payload.allowed === true;
  return (
    <div className="space-y-2 text-xs">
      <p className="text-muted-foreground">
        {allowed ? t.gatesPass : t.gatesBlock}
      </p>
      <ul className="space-y-1">
        {verdicts.map((row) => {
          if (!row || typeof row !== "object") return null;
          const item = row as Record<string, unknown>;
          const id = String(item.id ?? "");
          const label = gateLabel(id, locale) || String(item.name ?? id);
          const status = String(item.status ?? "");
          return (
            <li key={id}>
              <span className="font-medium">{label}</span>
              {" — "}
              {status}
              {item.reason ? ` — ${String(item.reason)}` : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function renderArtifactBody(
  artifact: TradingArtifact,
  locale?: string | null,
) {
  const payload = artifact.payload ?? {};
  switch (artifact.type) {
    case "chart_snapshot":
      return <ChartSnapshotArtifact artifact={artifact} />;
    case "level_map":
      return <LevelMapArtifact artifact={artifact} locale={locale} />;
    case "gate_report":
      return <GateReportArtifact artifact={artifact} locale={locale} />;
    case "decision":
      return (
        <div className="space-y-1 text-sm">
          <div className="font-semibold uppercase">{String(payload.decision ?? "")}</div>
          <p className="text-muted-foreground">{String(payload.summary ?? "")}</p>
        </div>
      );
    case "key_reasons": {
      const reasons = Array.isArray(payload.reasons) ? payload.reasons : [];
      return (
        <ul className="list-disc space-y-1 pl-4 text-xs">
          {reasons.map((reason, index) => (
            <li key={`reason-${index}`}>{String(reason)}</li>
          ))}
        </ul>
      );
    }
    case "macro_dashboard": {
      const drivers = Array.isArray(payload.drivers) ? payload.drivers : [];
      return (
        <ul className="space-y-1 text-xs">
          {drivers.map((driver, index) => {
            if (!driver || typeof driver !== "object") return null;
            const item = driver as Record<string, unknown>;
            const name = String(item.name ?? `driver-${index}`);
            return (
              <li key={`${name}-${index}`}>
                <span className="font-medium">{name}</span>
                {": "}
                {String(item.bias ?? "neutral")}
                {item.strength != null ? ` (${String(item.strength)})` : ""}
              </li>
            );
          })}
        </ul>
      );
    }
    case "price_quote": {
      const t = cardStrings(locale);
      return (
        <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
          <div>
            <span className="text-muted-foreground">{t.bid}</span>
            <div className="font-medium">{String(payload.bid ?? "—")}</div>
          </div>
          <div>
            <span className="text-muted-foreground">{t.ask}</span>
            <div className="font-medium">{String(payload.ask ?? "—")}</div>
          </div>
          <div>
            <span className="text-muted-foreground">{t.mid}</span>
            <div className="font-medium">{String(payload.mid ?? "—")}</div>
          </div>
          <div>
            <span className="text-muted-foreground">{t.state}</span>
            <div className="font-medium">
              {payload.tradeable === true ? t.tradeable : t.nonTradeable}
            </div>
          </div>
        </div>
      );
    }
    case "plan_status": {
      const t = cardStrings(locale);
      const targets = Array.isArray(payload.targets) ? payload.targets : [];
      return (
        <div className="space-y-2 text-xs">
          <div className="font-semibold uppercase">
            {String(payload.direction ?? "")} · {String(payload.status ?? "")}
          </div>
          {payload.livePrice != null ? (
            <p className="text-muted-foreground">
              {t.live}: {String(payload.livePrice)}
            </p>
          ) : null}
          <p className="text-muted-foreground">{String(payload.summary ?? "")}</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div>
              <span className="text-muted-foreground">{t.entry}</span>
              <div className="font-medium">{String(payload.entry ?? "—")}</div>
            </div>
            <div>
              <span className="text-muted-foreground">{t.stop}</span>
              <div className="font-medium">{String(payload.stopLoss ?? "—")}</div>
            </div>
            {targets.map((target, index) => (
              <div key={`plan-tp-${index}`}>
                <span className="text-muted-foreground">{t.target}{index + 1}</span>
                <div className="font-medium">{String(target)}</div>
              </div>
            ))}
          </div>
        </div>
      );
    }
    default:
      return (
        <pre className="whitespace-pre-wrap break-words text-xs text-muted-foreground">
          {JSON.stringify(payload, null, 2)}
        </pre>
      );
  }
}

export function ArtifactRenderer({ artifacts, locale }: ArtifactRendererProps) {
  if (!artifacts.length) {
    return null;
  }
  return (
    <div className="flex flex-col gap-3">
      {artifacts.map((artifact, index) => (
        <article
          key={`${artifact.type}-${index}`}
          className="rounded-lg border bg-card p-4 text-sm shadow-sm"
        >
          <header className="mb-2 font-medium">
            {artifact.title ?? artifact.type}
          </header>
          {renderArtifactBody(artifact, locale)}
        </article>
      ))}
    </div>
  );
}
