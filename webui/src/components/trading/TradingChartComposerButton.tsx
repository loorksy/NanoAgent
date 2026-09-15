import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { CandlestickChart } from "lucide-react";
import { useTranslation } from "react-i18next";

interface TradingChartComposerButtonProps {
  open: boolean;
  disabled?: boolean;
  isHero?: boolean;
  onToggle: () => void;
}

export function TradingChartComposerButton({
  open,
  disabled = false,
  isHero = false,
  onToggle,
}: TradingChartComposerButtonProps) {
  const { t } = useTranslation();
  const label = open
    ? t("trading.chart.hideChart", { defaultValue: "Hide chart" })
    : t("trading.chart.showChart", { defaultValue: "Show chart" });

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            disabled={disabled}
            aria-label={label}
            aria-pressed={open}
            onClick={onToggle}
            className={cn(
              "thread-composer-action touch-target rounded-full border border-transparent text-muted-foreground hover:bg-muted/65 hover:text-foreground",
              isHero ? "h-8 w-8" : "h-9 w-9",
              open && "border-primary/35 bg-primary/10 text-primary hover:bg-primary/15 hover:text-primary",
            )}
          >
            <CandlestickChart className={cn(isHero ? "h-4 w-4" : "h-4 w-4")} />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">{label}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
