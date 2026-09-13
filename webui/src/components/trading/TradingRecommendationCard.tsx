import { AgentCards } from "@/components/trading/AgentCards";
import { ArtifactRenderer } from "@/components/trading/ArtifactRenderer";
import { TradingStageChecklist } from "@/components/trading/TradingStageChecklist";
import { TradingTeamPanel } from "@/components/trading/TradingTeamPanel";
import { Button } from "@/components/ui/button";
import type { TradingResultWire } from "@/lib/trading/types";
import { useClient } from "@/providers/ClientProvider";
import { useCallback, useState } from "react";

interface TradingRecommendationCardProps {
  result: TradingResultWire;
  stages?: TradingResultWire["stages"];
  showStages?: boolean;
}

export function TradingRecommendationCard({
  result,
  stages = result.stages,
  showStages = true,
}: TradingRecommendationCardProps) {
  const { getToken } = useClient();
  const [paperStatus, setPaperStatus] = useState<string | null>(null);
  const rec = result.recommendation;
  const decision = result.decision.toUpperCase();

  const onPaper = useCallback(async (action: "approve" | "reject") => {
    if (!result.recommendationId) return;
    const token = getToken();
    const res = await fetch(
      `/api/trading/paper?recommendation_id=${encodeURIComponent(result.recommendationId)}&action=${action}`,
      { headers: token ? { Authorization: `Bearer ${token}` } : {} },
    );
    if (res.ok) {
      setPaperStatus(action === "approve" ? "Approved (paper)" : "Rejected");
    }
  }, [getToken, result.recommendationId]);

  return (
    <div className="rounded-xl border bg-card p-4 shadow-sm">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-lg font-semibold uppercase tracking-wide">{decision}</div>
          <p className="text-sm text-muted-foreground">{result.summary}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Confidence {(result.confidence * 100).toFixed(0)}%
          </p>
        </div>
        {result.recommendationId && decision !== "WAIT" ? (
          <div className="flex gap-2">
            <Button size="sm" variant="default" onClick={() => void onPaper("approve")}>
              Approve
            </Button>
            <Button size="sm" variant="outline" onClick={() => void onPaper("reject")}>
              Reject
            </Button>
          </div>
        ) : null}
      </div>

      {rec?.entry != null ? (
        <div className="mb-3 grid grid-cols-2 gap-2 rounded-lg bg-muted/40 p-3 text-xs sm:grid-cols-4">
          <div><span className="text-muted-foreground">Entry</span><div className="font-medium">{rec.entry.toFixed(2)}</div></div>
          {rec.stopLoss != null ? (
            <div><span className="text-muted-foreground">SL</span><div className="font-medium">{rec.stopLoss.toFixed(2)}</div></div>
          ) : null}
          {rec.targets?.[0] != null ? (
            <div><span className="text-muted-foreground">TP1</span><div className="font-medium">{rec.targets[0].toFixed(2)}</div></div>
          ) : null}
          {rec.targets?.[1] != null ? (
            <div><span className="text-muted-foreground">TP2</span><div className="font-medium">{rec.targets[1].toFixed(2)}</div></div>
          ) : null}
        </div>
      ) : null}

      {paperStatus ? (
        <p className="mb-2 text-xs text-muted-foreground">{paperStatus}</p>
      ) : null}

      {result.macroDrivers && result.macroDrivers.length > 0 ? (
        <div className="mb-3 rounded-lg border bg-muted/20 p-3">
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Macro drivers
          </div>
          <ul className="space-y-1 text-xs">
            {result.macroDrivers.map((item, index) => {
              const name = item.driver || item.name || `driver-${index}`;
              if (item.ran === false) {
                return (
                  <li key={`${name}-${index}`} className="text-muted-foreground">
                    <span className="font-medium">{name}</span>
                    {" — skipped — cache/not relevant"}
                  </li>
                );
              }
              const rationale = item.one_line_rationale || "";
              return (
                <li key={`${name}-${index}`}>
                  <span className="font-medium">{name}</span>
                  {": "}
                  {item.bias || "neutral"}
                  {item.strength != null ? ` ${item.strength}` : ""}
                  {rationale ? ` — ${rationale}` : ""}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {showStages && stages && stages.length > 0 ? (
        <div className="mb-3">
          <TradingStageChecklist stages={stages} compact />
        </div>
      ) : null}

      {result.teamAgents && result.teamAgents.length > 0 ? (
        <div className="mb-3">
          <TradingTeamPanel
            agents={result.teamAgents}
            teamMode={result.teamMode}
            compact
          />
        </div>
      ) : null}

      {result.artifacts && result.artifacts.length > 0 ? (
        <ArtifactRenderer artifacts={result.artifacts} locale={result.locale} />
      ) : result.cards && result.cards.length > 0 ? (
        <AgentCards
          cards={result.cards as Array<{ kind: string } & Record<string, unknown>>}
          locale={result.locale}
        />
      ) : null}
    </div>
  );
}
