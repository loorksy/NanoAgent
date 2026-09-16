import { normalizeTradingLocale } from "@/lib/trading/cardLocale";

/** Mirrors `GATE_LABELS` in `nanobot/trading/i18n.py`. Wire ids stay G1…G20; UI never shows them. */
const GATE_LABELS = {
  en: {
    G1: "News & event shield",
    G2: "Liquidity alignment",
    G3: "Supply & demand zones",
    G4: "Structure & chart confirmation",
    G6: "Risk geometry",
    G7: "Live price confirmation",
    G8: "Minimum reward-to-risk",
    G9: "Spread guard",
    G10: "Cooldown lock",
    G11: "Open-position cap",
    G12: "Drawdown & kill switch",
    G13: "Live quote freshness",
    G14: "Pending-order validity",
    G15: "Session & calendar lock",
    G16: "Bad-tick filter",
    G17: "News operational freeze",
    G18: "Margin guard",
    G19: "Slippage & latency",
    G20: "Position sizing",
  },
  ar: {
    G1: "درع الأخبار والأحداث",
    G2: "مواءمة السيولة",
    G3: "مناطق العرض والطلب",
    G4: "تأكيد الهيكل والرسم البياني",
    G6: "هندسة المخاطر",
    G7: "تأكيد السعر الحي",
    G8: "الحد الأدنى للعائد مقابل المخاطرة",
    G9: "حارس السبريد",
    G10: "قفل التهدئة",
    G11: "سقف الصفقات المفتوحة",
    G12: "قاطع التراجع ومفتاح الإيقاف",
    G13: "حداثة السعر الحي",
    G14: "صلاحية الأوامر المعلقة",
    G15: "قفل الجلسة والتقويم",
    G16: "فلتر الأسعار الشاذة",
    G17: "تجميد تشغيلي للأخبار",
    G18: "حارس الهامش",
    G19: "الانزلاق وزمن التنفيذ",
    G20: "ضبط حجم العقد",
  },
} as const;

const RAW_GATE_ID = /^G\d+$/i;

export function gateLabel(gateId: string, locale?: string | null): string {
  const loc = normalizeTradingLocale(locale);
  const map = GATE_LABELS[loc];
  const key = gateId.trim().toUpperCase();
  return map[key as keyof typeof map] ?? "";
}

/** Operator-facing name from the i18n map. Never returns G1…G20. */
export function displayGateName(
  item: { id?: unknown; name?: unknown },
  locale?: string | null,
): string {
  const id = String(item.id ?? "").trim();
  const mapped = gateLabel(id, locale);
  if (mapped) {
    return mapped;
  }
  const name = String(item.name ?? "").trim();
  if (name && !RAW_GATE_ID.test(name)) {
    return name;
  }
  return gateLabel(name, locale);
}
