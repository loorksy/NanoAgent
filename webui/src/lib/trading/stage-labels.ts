import { normalizeTradingLocale } from "@/lib/trading/cardLocale";

const STAGE_LABELS = {
  en: {
    market_data: "Reading live market",
    structure: "Mapping price structure",
    liquidity: "Scanning liquidity",
    supply_demand: "Locating key zones",
    multi_timeframe: "Cross-timeframe read",
    news: "Calendar & headline scan",
    risk: "Building trade scenarios",
    final_decision: "Forming the call",
    drawing: "Marking the chart",
    execution_guard: "Final safety check",
    general: "Response",
    research: "Research",
    macro_drivers: "Macro pulse",
  },
  ar: {
    market_data: "قراءة السوق الحي",
    structure: "رسم الهيكل السعاري",
    liquidity: "مسح السيولة",
    supply_demand: "تحديد المناطق الحاسمة",
    multi_timeframe: "قراءة الأطر المتعددة",
    news: "مراجعة التقويم والأخبار",
    risk: "بناء السيناريوهات",
    final_decision: "صياغة القرار",
    drawing: "وسم الرسم البياني",
    execution_guard: "الفحص الأمني النهائي",
    general: "الإجابة",
    research: "البحث",
    macro_drivers: "نبض الاقتصاد الكلي",
  },
} as const;

/** @deprecated use stageLabel(stage, locale) */
export const STAGE_LABEL_EN: Record<string, string> = STAGE_LABELS.en;

export function stageLabel(stage: string, locale?: string | null): string {
  const loc = normalizeTradingLocale(locale);
  const map = STAGE_LABELS[loc];
  return map[stage as keyof typeof map] ?? stage;
}
