import { normalizeTradingLocale } from "@/lib/trading/cardLocale";

const GATE_LABELS = {
  en: {
    G1: "News & event shield",
    G2: "Liquidity alignment",
    G3: "Supply & demand zones",
    G4: "Structure & chart confirmation",
    G6: "Risk geometry",
    G7: "Live price confirmation",
  },
  ar: {
    G1: "درع الأخبار والأحداث",
    G2: "مواءمة السيولة",
    G3: "مناطق العرض والطلب",
    G4: "تأكيد الهيكل والرسم البياني",
    G6: "هندسة المخاطر",
    G7: "تأكيد السعر الحي",
  },
} as const;

export function gateLabel(gateId: string, locale?: string | null): string {
  const loc = normalizeTradingLocale(locale);
  const map = GATE_LABELS[loc];
  return map[gateId as keyof typeof map] ?? gateId;
}
