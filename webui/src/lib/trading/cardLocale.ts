export type TradingCardLocale = "ar" | "en";

export function normalizeTradingLocale(locale?: string | null): TradingCardLocale {
  return locale?.toLowerCase().startsWith("ar") ? "ar" : "en";
}

const STRINGS = {
  en: {
    noCards: "No recommendation cards yet.",
    gatesPass: "All required gates passed.",
    gatesBlock: "Recommendation blocked by gates.",
    pass: "Pass",
    veto: "Veto",
    unavailable: "Unavailable",
    entry: "Entry",
    stop: "Stop loss",
    target: "Target",
    plan: "Plan",
    state: "Status",
    visualState: "Visual state",
    skipped: "Skipped",
    confidence: "Confidence",
    tracking: "Tracking",
    on: "on",
    bid: "Bid",
    ask: "Ask",
    mid: "Mid",
    tradeable: "Tradeable",
    nonTradeable: "Non-tradeable",
    live: "Live price",
  },
  ar: {
    noCards: "لا توجد بطاقات توصية بعد.",
    gatesPass: "اجتازت جميع البوابات المطلوبة.",
    gatesBlock: "حُجبت التوصية بسبب البوابات.",
    pass: "ناجح",
    veto: "مرفوض",
    unavailable: "غير متاح",
    entry: "نقطة الدخول",
    stop: "وقف الخسارة",
    target: "الهدف",
    plan: "الخطة",
    state: "الحالة",
    visualState: "الحالة البصرية",
    skipped: "تم التخطي",
    confidence: "مستوى الثقة",
    tracking: "المتابعة",
    on: "على",
    bid: "سعر الشراء",
    ask: "سعر البيع",
    mid: "السعر الوسطي",
    tradeable: "قابل للتداول",
    nonTradeable: "غير قابل للتداول",
    live: "السعر الحالي",
  },
} as const;

export function cardStrings(locale?: string | null) {
  return STRINGS[normalizeTradingLocale(locale)];
}

export function cardKindTitle(kind: string, locale?: string | null): string {
  const loc = normalizeTradingLocale(locale);
  const map: Record<TradingCardLocale, Record<string, string>> = {
    en: {
      decision: "Decision",
      plan_levels: "Plan levels",
      activation: "Activation",
      invalidation: "Invalidation",
      gate_checklist: "Gate checklist",
      visual_review: "Visual review",
      macro_drivers: "Macro drivers",
      key_reasons: "Key reasons",
      risk_warnings: "Risk warnings",
      tracked_recommendation: "Tracked recommendation",
      scenario_notice: "Scenario notice",
      price_quote: "Gold quote",
      plan_status: "Plan status",
      chart_snapshot: "Chart snapshot",
    },
    ar: {
      decision: "القرار",
      plan_levels: "مستويات الخطة",
      activation: "التفعيل",
      invalidation: "الإبطال",
      gate_checklist: "قائمة البوابات",
      visual_review: "المراجعة البصرية",
      macro_drivers: "محركات الاقتصاد الكلي",
      key_reasons: "أبرز المبررات",
      risk_warnings: "تحذيرات المخاطر",
      tracked_recommendation: "التوصية النشطة",
      scenario_notice: "ملاحظة السيناريو",
      price_quote: "سعر الذهب",
      plan_status: "حالة الخطة",
      chart_snapshot: "لقطة الرسم البياني",
    },
  };
  return map[loc][kind] ?? kind.replace(/_/g, " ");
}
