import type {
  EntityId,
  IChartingLibraryWidget,
} from "../../../../vendor/tradingview/charting_library/charting_library";

export interface TradingDrawingWire {
  type: string;
  label: string;
  color: string;
  points: Array<{ time?: number; price?: number }>;
  fill?: boolean;
}

let shapeIds: EntityId[] = [];

export function clearTradingDrawings(widget: IChartingLibraryWidget | null | undefined) {
  if (!widget) return;
  const chart = widget.activeChart();
  for (const id of shapeIds) {
    try {
      chart.removeEntity(id);
    } catch {
      // ignore stale ids
    }
  }
  shapeIds = [];
}

export async function applyTradingDrawings(
  widget: IChartingLibraryWidget | null | undefined,
  drawings: TradingDrawingWire[],
) {
  if (!widget || drawings.length === 0) return;
  clearTradingDrawings(widget);
  const chart = widget.activeChart();
  for (const drawing of drawings) {
    const price = drawing.points[0]?.price;
    if (price == null) continue;
    try {
      if (
        drawing.type === "price_line"
        || drawing.type === "entry"
        || drawing.type === "stop"
        || drawing.type === "target"
        || drawing.type === "tp"
      ) {
        const id = await chart.createShape(
          { time: Math.floor(Date.now() / 1000), price },
          {
            shape: "horizontal_line",
            text: drawing.label,
            overrides: {
              linecolor: drawing.color,
              linewidth: 2,
            },
          },
        );
        if (id) shapeIds.push(id as EntityId);
      }
    } catch {
      // TV may reject shapes before chart is ready
    }
  }
}
