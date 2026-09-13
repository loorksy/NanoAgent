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
    stop: "Stop",
    target: "TP",
    plan: "Plan",
    state: "State",
    visualState: "Visual state",
    skipped: "skipped",
    confidence: "Confidence",
    tracking: "Tracking",
    on: "on",
  },
  ar: {
    noCards: "لا توجد بطاقات توصية بعد.",
    gatesPass: "جميع البوابات المطلوبة ناجحة.",
    gatesBlock: "التوصية محجوبة من البوابات.",
    pass: "ناجح",
    veto: "رفض",
    unavailable: "غير متاح",
    entry: "الدخول",
    stop: "الوقف",
    target: "الهدف",
    plan: "الخطة",
    state: "الحالة",
    visualState: "الحالة البصرية",
    skipped: "تخطى",
    confidence: "الثقة",
    tracking: "متابعة",
    on: "على",
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
    },
    ar: {
      decision: "القرار",
      plan_levels: "مستويات الخطة",
      activation: "التفعيل",
      invalidation: "الإبطال",
      gate_checklist: "قائمة البوابات",
      visual_review: "المراجعة البصرية",
      macro_drivers: "محركات الاقتصاد الكلي",
      key_reasons: "الأسباب الرئيسية",
      risk_warnings: "تحذيرات المخاطر",
      tracked_recommendation: "التوصية المتتبعة",
      scenario_notice: "ملاحظة السيناريو",
    },
  };
  return map[loc][kind] ?? kind.replace(/_/g, " ");
}
