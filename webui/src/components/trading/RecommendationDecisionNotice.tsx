import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AlertTriangle, LoaderCircle } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

export interface SupersedeDecisionPayload {
  session_key: string;
  live_recommendation: {
    id: string;
    direction?: string;
    entry?: number | null;
    stop_loss?: number | null;
    targets?: number[];
    live_price?: number | null;
    status?: string;
  };
}

interface RecommendationDecisionNoticeProps {
  payload: SupersedeDecisionPayload;
  onResolved: () => void;
}

export function RecommendationDecisionNotice({
  payload,
  onResolved,
}: RecommendationDecisionNoticeProps) {
  const { t } = useTranslation();
  const [pending, setPending] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const live = payload.live_recommendation;
  const direction = (live.direction || "wait").toUpperCase();

  const run = async (action: "approve_new" | "reject_new") => {
    setPending(action === "approve_new" ? "approve" : "reject");
    setError(null);
    try {
      const res = await fetch("/api/trading/recommendations/transition", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          session_key: payload.session_key,
          recommendation_id: live.id,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({})) as { error?: string };
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      onResolved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setPending(null);
    }
  };

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="mx-auto mb-2 flex w-full max-w-[49.5rem] flex-col gap-2 rounded-control border border-amber-500/40 bg-amber-500/10 px-3 py-3 text-sm sm:flex-row sm:items-center"
    >
      <AlertTriangle className="hidden h-4 w-4 shrink-0 text-amber-500 sm:block" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="font-medium">
          {t("supersede.prompt", {
            defaultValue: "You have an active recommendation. Approve to close it and issue a new one.",
          })}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {direction} · entry {live.entry ?? "—"} · SL {live.stop_loss ?? "—"}
          {live.live_price != null ? ` · now ${live.live_price.toFixed(2)}` : ""}
        </p>
        {error ? <p className={cn("mt-1 text-xs text-destructive")}>{error}</p> : null}
      </div>
      <div className="flex shrink-0 gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={pending !== null}
          onClick={() => void run("reject_new")}
        >
          {pending === "reject" ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : null}
          {t("supersede.reject_btn", { defaultValue: "Keep current" })}
        </Button>
        <Button
          type="button"
          size="sm"
          disabled={pending !== null}
          onClick={() => void run("approve_new")}
        >
          {pending === "approve" ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : null}
          {t("supersede.approve_btn", { defaultValue: "Approve new" })}
        </Button>
      </div>
    </div>
  );
}
