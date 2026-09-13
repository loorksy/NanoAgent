"""Central trading message catalog — user-facing strings only (professional Arabic)."""

from __future__ import annotations

from typing import Any

from nanobot.trading.locale import normalize_locale

# ---------------------------------------------------------------------------
# Artifact titles
# ---------------------------------------------------------------------------
ARTIFACT_TITLES: dict[str, dict[str, str]] = {
    "en": {
        "decision": "Decision",
        "level_map": "Plan levels",
        "gate_report": "Quality checks",
        "chart_snapshot": "Chart snapshot",
        "macro_dashboard": "Macro drivers",
        "key_reasons": "Key reasons",
        "visual_review": "Visual review",
        "team_briefing": "Team briefing",
        "tracked_plan": "Tracked plan",
        "price_quote": "Gold quote",
        "plan_status": "Plan status",
    },
    "ar": {
        "decision": "القرار",
        "level_map": "مستويات الخطة",
        "gate_report": "فحوصات الجودة",
        "chart_snapshot": "لقطة الرسم البياني",
        "macro_dashboard": "محركات الاقتصاد الكلي",
        "key_reasons": "أبرز المبررات",
        "visual_review": "المراجعة البصرية",
        "team_briefing": "ملخص الفريق",
        "tracked_plan": "الخطة النشطة",
        "price_quote": "سعر الذهب",
        "plan_status": "حالة الخطة",
    },
}

# ---------------------------------------------------------------------------
# Pipeline stage labels (progress UI)
# ---------------------------------------------------------------------------
STAGE_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "market_data": "Reading live market",
        "structure": "Mapping price structure",
        "liquidity": "Scanning liquidity",
        "supply_demand": "Locating key zones",
        "multi_timeframe": "Cross-timeframe read",
        "news": "Calendar & headline scan",
        "risk": "Building trade scenarios",
        "final_decision": "Forming the call",
        "drawing": "Marking the chart",
        "execution_guard": "Final safety check",
        "general": "Response",
        "research": "Research",
        "macro_drivers": "Macro pulse",
    },
    "ar": {
        "market_data": "قراءة السوق الحي",
        "structure": "رسم الهيكل السعاري",
        "liquidity": "مسح السيولة",
        "supply_demand": "تحديد المناطق الحاسمة",
        "multi_timeframe": "قراءة الأطر المتعددة",
        "news": "مراجعة التقويم والأخبار",
        "risk": "بناء السيناريوهات",
        "final_decision": "صياغة القرار",
        "drawing": "وسم الرسم البياني",
        "execution_guard": "الفحص الأمني النهائي",
        "general": "الإجابة",
        "research": "البحث",
        "macro_drivers": "نبض الاقتصاد الكلي",
    },
}

# ---------------------------------------------------------------------------
# Quality-check labels (user-facing; internal ids stay G1, G2, … in wire only)
# ---------------------------------------------------------------------------
GATE_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "G1": "News & event shield",
        "G2": "Liquidity alignment",
        "G3": "Supply & demand zones",
        "G4": "Structure & chart confirmation",
        "G6": "Risk geometry",
        "G7": "Live price confirmation",
    },
    "ar": {
        "G1": "درع الأخبار والأحداث",
        "G2": "مواءمة السيولة",
        "G3": "مناطق العرض والطلب",
        "G4": "تأكيد الهيكل والرسم البياني",
        "G6": "هندسة المخاطر",
        "G7": "تأكيد السعر الحي",
    },
}

# ---------------------------------------------------------------------------
# Card / channel formatting labels
# ---------------------------------------------------------------------------
CARD_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "recommendation": "Recommendation",
        "confidence": "Confidence",
        "entry": "Entry",
        "stop": "Stop loss",
        "target": "Target",
        "reasons": "Reasons",
        "macro": "Macro drivers",
        "gates_pass": "All quality checks passed",
        "gates_block": "Recommendation held — a quality check did not pass",
        "disclaimer": "Recommendations only — no execution.",
        "trend": "Trend",
        "bias": "Bias",
        "signal": "Signal",
        "skipped": "Skipped — cache or not applicable",
        "tradeable": "Tradeable",
        "non_tradeable": "Non-tradeable",
        "bid": "Bid",
        "ask": "Ask",
        "mid": "Mid",
        "state": "Status",
        "live": "Live price",
    },
    "ar": {
        "recommendation": "التوصية",
        "confidence": "مستوى الثقة",
        "entry": "نقطة الدخول",
        "stop": "وقف الخسارة",
        "target": "الهدف",
        "reasons": "المبررات",
        "macro": "محركات الاقتصاد الكلي",
        "gates_pass": "اجتازت جميع فحوصات الجودة",
        "gates_block": "أُوقفت التوصية — لم يجتز أحد فحوصات الجودة",
        "disclaimer": "توصيات تحليلية فقط — دون تنفيذ.",
        "trend": "الاتجاه",
        "bias": "التحيز",
        "signal": "الإشارة",
        "skipped": "تم التخطي — مخزن مؤقت أو غير منطبق",
        "tradeable": "قابل للتداول",
        "non_tradeable": "غير قابل للتداول",
        "bid": "سعر الشراء",
        "ask": "سعر البيع",
        "mid": "السعر الوسطي",
        "state": "الحالة",
        "live": "السعر الحالي",
    },
}

TREND_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "up": "up",
        "down": "down",
        "bullish": "bullish",
        "bearish": "bearish",
        "neutral": "neutral",
        "sideways": "sideways",
        "range": "range",
    },
    "ar": {
        "up": "صاعد",
        "down": "هابط",
        "bullish": "صاعد",
        "bearish": "هابط",
        "neutral": "محايد",
        "sideways": "عرضي",
        "range": "عرضي",
    },
}

BIAS_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "up": "up",
        "down": "down",
        "bullish": "bullish",
        "bearish": "bearish",
        "neutral": "neutral",
        "sideways": "sideways",
        "range": "range",
    },
    "ar": {
        "up": "صعودي",
        "down": "هبوطي",
        "bullish": "صعودي",
        "bearish": "هبوطي",
        "neutral": "محايد",
        "sideways": "عرضي",
        "range": "عرضي",
    },
}

SETUP_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "structure_break": "structure break",
        "structure": "structure",
        "breakout": "breakout",
        "supply": "supply zone",
        "demand": "demand zone",
        "liquidity_sweep": "liquidity sweep",
    },
    "ar": {
        "structure_break": "كسر الهيكل السعاري",
        "structure": "الهيكل السعاري",
        "breakout": "اختراق",
        "supply": "منطقة عرض",
        "demand": "منطقة طلب",
        "liquidity_sweep": "سحب السيولة",
    },
}

DECISION_LABELS: dict[str, tuple[str, str, str]] = {
    "buy": ("🟢", "شراء", "BUY"),
    "sell": ("🔴", "بيع", "SELL"),
    "wait": ("⚪", "انتظار", "WAIT"),
}

DRIVER_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "geopolitical_safehaven": "Geopolitical safe haven",
        "dxy": "US dollar (DXY)",
        "us_macro_data": "US macro data",
        "us_real_yields_fomc": "Real yields / FOMC",
        "fund_flows_positioning": "Fund flows",
        "central_bank_demand": "Central bank demand",
        "seasonal_physical_demand": "Seasonal physical demand",
    },
    "ar": {
        "geopolitical_safehaven": "الملاذ الجيوسياسي",
        "dxy": "مؤشر الدولار",
        "us_macro_data": "البيانات الاقتصادية الأمريكية",
        "us_real_yields_fomc": "العوائد الحقيقية / الفيدرالي",
        "fund_flows_positioning": "تدفقات الصناديق",
        "central_bank_demand": "طلب البنوك المركزية",
        "seasonal_physical_demand": "الطلب الموسمي المادي",
    },
}

OUTCOME_STATUS_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "waiting": "Waiting for activation",
        "in_trade": "In trade",
        "tp1": "First target reached",
        "invalidated": "Invalidated (stop loss)",
        "valid_now": "Valid now",
        "awaiting_activation": "Awaiting activation",
        "expired": "Expired",
    },
    "ar": {
        "waiting": "بانتظار التفعيل",
        "in_trade": "داخل الصفقة",
        "tp1": "تحقق الهدف الأول",
        "invalidated": "أُبطلت (وقف الخسارة)",
        "valid_now": "سارية",
        "awaiting_activation": "بانتظار التفعيل",
        "expired": "منتهية الصلاحية",
    },
}

OUTCOME_FIELD_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Gold recommendation update",
        "status": "Status",
        "live": "Live price",
        "entry": "Entry",
        "stop": "Stop",
        "targets": "Targets",
    },
    "ar": {
        "title": "تحديث توصية الذهب",
        "status": "الحالة",
        "live": "السعر الحالي",
        "entry": "نقطة الدخول",
        "stop": "وقف الخسارة",
        "targets": "الأهداف",
    },
}

# ---------------------------------------------------------------------------
# Message templates (keyed strings with optional {placeholders})
# ---------------------------------------------------------------------------
MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "price.header": "XAUUSD live quote",
        "price.footer": "Live market feed — ask for a full gold analysis when needed.",
        "price.feed_unconfigured": "Market data is not available — cannot fetch the live gold quote.",
        "price.fetch_failed": "Could not read the live gold price: {error}",
        "price.no_quote": "No live quote is available right now.",
        "analysis.failed": "Gold analysis could not be completed: {error}",
        "analysis.no_result": "Analysis produced no result.",
        "analysis.feed_unconfigured": "Market data is not available — cannot run gold analysis.",
        "stage.opening_chart": "Opening gold chart…",
        "capture.webui_required": (
            "Chart capture requires the WebUI with the gold chart panel open. "
            "Open the chat in the web interface and try again."
        ),
        "capture.no_frames": "No chart image was captured. Open the chart panel and try again.",
        "capture.snapshot_title": "Gold chart snapshot ({interval})",
        "followup.no_live_plan": "No live recommendation.",
        "followup.summary": (
            "Live plan remains {direction}. Status: {status}. "
            "This is a follow-up, not a new recommendation."
        ),
        "followup.no_second_rec": (
            " A second recommendation is not issued while this plan is live."
        ),
        "warning.ungrounded_levels": (
            "Direction is clear, but proposed levels were not grounded in evidence and were dropped."
        ),
        "warning.mtf_conflict": (
            "Conflicting timeframe or competing evidence — plan kept conditional pending confirmation."
        ),
        "warning.activation_printed": (
            "Activation already printed — plan converted to immediate follow-through."
        ),
        "card.invalidation_at_stop": "Invalidated if price reaches {stop}",
        "gate.buy_near_liquidity": "Buy entry too close to overhead liquidity ({distance})",
        "gate.sell_near_liquidity": "Sell entry too close to downside liquidity ({distance})",
        "gate.buy_against_sweep": "Buy against recent upside liquidity sweep",
        "gate.sell_against_sweep": "Sell against recent downside liquidity sweep",
        "gate.buy_in_supply": "Buy entry inside supply zone",
        "gate.sell_in_demand": "Sell entry inside demand zone",
        "display.gold": "Gold",
    },
    "ar": {
        "price.header": "سعر الذهب (XAUUSD)",
        "price.footer": "بيانات السوق الحية — لطلب تحليل كامل، اطلب «حلّل الذهب».",
        "price.feed_unconfigured": "بيانات السوق غير متاحة — لا يمكن جلب سعر الذهب الحي.",
        "price.fetch_failed": "تعذّر قراءة سعر الذهب الحي: {error}",
        "price.no_quote": "لا يوجد سعر حي متاح حالياً.",
        "analysis.failed": "تعذّر إكمال تحليل الذهب: {error}",
        "analysis.no_result": "لم يُنتج التحليل أي نتيجة.",
        "analysis.feed_unconfigured": "بيانات السوق غير متاحة — لا يمكن تشغيل تحليل الذهب.",
        "stage.opening_chart": "فتح رسم الذهب…",
        "capture.webui_required": (
            "يتطلب التقاط الرسم البياني فتح الواجهة مع لوحة الرسم البياني. "
            "افتح المحادثة من الواجهة ثم أعد الطلب."
        ),
        "capture.no_frames": (
            "لم تُلتقط أي صورة للرسم البياني. تأكد من فتح اللوحة ثم أعد المحاولة."
        ),
        "capture.snapshot_title": "لقطة الرسم البياني للذهب ({interval})",
        "followup.no_live_plan": "لا توجد توصية نشطة حالياً.",
        "followup.summary": (
            "التوصية النشطة ما زالت {direction}. التقييم: {status}. "
            "هذه متابعة وليست توصية جديدة."
        ),
        "followup.no_second_rec": " لا يمكن إصدار توصية ثانية فيما تبقى الخطة الحالية سارية.",
        "warning.ungrounded_levels": (
            "الاتجاه واضح، لكن المستويات المقترحة لم تُطابق مستويات الأدلة فلم تُعتمد."
        ),
        "warning.mtf_conflict": (
            "تعارض بين الأطر الزمنية أو أدلة متنافسة — أُبقيت الخطة مشروطة بانتظار التأكيد."
        ),
        "warning.activation_printed": (
            "تحقق شرط التفعيل مسبقاً — حُوّلت الخطة إلى تنفيذ فوري عند السعر الحالي."
        ),
        "card.invalidation_at_stop": "تُبطل إذا بلغ السعر {stop}",
        "gate.buy_near_liquidity": "دخول شراء قريب جداً من سيولة علوية ({distance})",
        "gate.sell_near_liquidity": "دخول بيع قريب جداً من سيولة سفلية ({distance})",
        "gate.buy_against_sweep": "شراء عكس سحب سيولة علوية حديث",
        "gate.sell_against_sweep": "بيع عكس سحب سيولة سفلية حديث",
        "gate.buy_in_supply": "دخول شراء داخل منطقة عرض",
        "gate.sell_in_demand": "دخول بيع داخل منطقة طلب",
        "display.gold": "الذهب",
    },
}


def _loc(locale: str | None) -> str:
    return "ar" if normalize_locale(locale) == "ar" else "en"


def tr(key: str, locale: str | None = None, **kwargs: Any) -> str:
    """Look up a message template for the locale and format placeholders."""
    loc = _loc(locale)
    template = MESSAGES[loc].get(key) or MESSAGES["en"].get(key) or key
    if kwargs:
        return template.format(**kwargs)
    return template


def label_map(name: str, locale: str | None = None) -> dict[str, str]:
    """Return a label dictionary for card/artifact/stage lookups."""
    loc = _loc(locale)
    catalogs: dict[str, dict[str, dict[str, str]]] = {
        "card": CARD_LABELS,
        "artifact": ARTIFACT_TITLES,
        "stage": STAGE_LABELS,
        "gate": GATE_LABELS,
        "trend": TREND_LABELS,
        "bias": BIAS_LABELS,
        "setup": SETUP_LABELS,
        "driver": DRIVER_LABELS,
        "outcome_status": OUTCOME_STATUS_LABELS,
        "outcome_field": OUTCOME_FIELD_LABELS,
    }
    catalog = catalogs.get(name, {})
    return catalog.get(loc, catalog.get("en", {}))


def artifact_title(kind: str, locale: str | None = None) -> str:
    return label_map("artifact", locale).get(kind, kind)


def stage_label(stage: str, locale: str | None = None) -> str:
    return label_map("stage", locale).get(stage, stage)


def gate_label(gate_id: str, locale: str | None = None) -> str:
    """User-facing quality-check name (never show raw G1, G2, … to operators)."""
    return label_map("gate", locale).get(gate_id, gate_id)
