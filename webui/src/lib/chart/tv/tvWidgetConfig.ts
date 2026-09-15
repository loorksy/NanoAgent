import type { ChartingLibraryWidgetOptions } from "../../../../vendor/tradingview/charting_library/charting_library";

/** TradingView chrome disabled for AiChart-style minimal chart (no toolbars). */
export const MINIMAL_TV_DISABLED_FEATURES = [
  "header_symbol_search",
  "symbol_search_hot_key",
  "header_compare",
  "left_toolbar",
  "header_widget",
  "timeframes_toolbar",
  "control_bar",
  "main_series_scale_menu",
  "legend_widget",
  "display_market_status",
  "header_saveload",
  "header_settings",
  "header_undo_redo",
  "header_screenshot",
  "header_fullscreen_button",
] as const;

export type TvChartVariant = "minimal" | "full";

export function tvDisabledFeatures(variant: TvChartVariant): ChartingLibraryWidgetOptions["disabled_features"] {
  if (variant === "full") {
    return ["header_symbol_search", "symbol_search_hot_key", "header_compare"];
  }
  return [...MINIMAL_TV_DISABLED_FEATURES];
}
