import { cn } from "@/lib/utils";
import { useQuoteStream } from "@/lib/trading/useQuoteStream";

export interface RecommendationCardRow {
  id: string;
  symbol: string;
  direction: string;
  entry: number | null;
  stop_loss: number | null;
  targets: number[];
  status: string;
  summary: string;
  confidence: number;
  created_at: number;
}

interface RecommendationCardProps {
  row: RecommendationCardRow;
  selected?: boolean;
  onSelect: () => void;
}

const OPEN = new Set(["valid_now", "awaiting_activation", "waiting", "in_trade"]);

function pnlPerOz(direction: string, entry: number | null, mid: number | null): number | null {
  if (entry == null || mid == null) return null;
  const dir = direction.toLowerCase();
  if (dir === "buy" || dir === "long") return mid - entry;
  if (dir === "sell" || dir === "short") return entry - mid;
  return null;
}

export function RecommendationCard({ row, selected, onSelect }: RecommendationCardProps) {
  const live = OPEN.has(row.status);
  const quote = useQuoteStream(row.symbol || "XAUUSD", live);
  const pnl = pnlPerOz(row.direction, row.entry, quote?.mid ?? null);
  const isBuy = row.direction.toLowerCase() === "buy";

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "group w-full rounded-xl border p-4 text-left transition-colors",
        "border-border/70 bg-card/80 hover:border-primary/40 hover:bg-card",
        selected && "border-primary/60 ring-1 ring-primary/30",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <span
            className={cn(
              "inline-flex rounded-md px-2 py-0.5 text-xs font-semibold",
              isBuy ? "bg-emerald-500/15 text-emerald-400" : "bg-rose-500/15 text-rose-400",
            )}
          >
            {row.direction.toUpperCase()}
          </span>
          <span className="ml-2 text-xs text-muted-foreground">{row.symbol}</span>
        </div>
        <span className="text-xs uppercase tracking-wide text-muted-foreground">{row.status.replaceAll("_", " ")}</span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div>
          <div className="text-xs text-muted-foreground">Entry</div>
          <div className="font-mono">{row.entry?.toFixed(2) ?? "—"}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">Now</div>
          <div className="font-mono">{quote?.mid?.toFixed(2) ?? "—"}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">SL</div>
          <div className="font-mono">{row.stop_loss?.toFixed(2) ?? "—"}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">P&amp;L / oz</div>
          <div className={cn("font-mono", pnl != null && pnl >= 0 ? "text-emerald-400" : "text-rose-400")}>
            {pnl != null ? `${pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}` : "—"}
          </div>
        </div>
      </div>
      {row.targets.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1">
          {row.targets.map((tp, index) => (
            <span key={`${row.id}-tp-${index}`} className="rounded bg-muted/60 px-1.5 py-0.5 text-xs font-mono">
              TP{index + 1} {tp.toFixed(2)}
            </span>
          ))}
        </div>
      ) : null}
      <p className="mt-3 line-clamp-2 text-xs text-muted-foreground">{row.summary}</p>
    </button>
  );
}
