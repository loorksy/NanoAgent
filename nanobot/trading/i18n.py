"""Central trading message catalog — user-facing strings only (professional Arabic)."""

from __future__ import annotations

import re
from typing import Any

from nanobot.trading.locale import normalize_locale

_RAW_GATE_ID = re.compile(r"^G\d+$", re.I)

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
        "G8": "Minimum reward-to-risk",
        "G9": "Spread guard",
        "G10": "Cooldown lock",
        "G11": "Open-position cap",
        "G12": "Drawdown & kill switch",
        "G13": "Live quote freshness",
        "G14": "Pending-order validity",
        "G15": "Session & calendar lock",
        "G16": "Bad-tick filter",
        "G17": "News operational freeze",
        "G18": "Margin guard",
        "G19": "Slippage & latency",
        "G20": "Position sizing",
    },
    "ar": {
        "G1": "درع الأخبار والأحداث",
        "G2": "مواءمة السيولة",
        "G3": "مناطق العرض والطلب",
        "G4": "تأكيد الهيكل والرسم البياني",
        "G6": "هندسة المخاطر",
        "G7": "تأكيد السعر الحي",
        "G8": "الحد الأدنى للعائد مقابل المخاطرة",
        "G9": "حارس السبريد",
        "G10": "قفل التهدئة",
        "G11": "سقف الصفقات المفتوحة",
        "G12": "قاطع التراجع ومفتاح الإيقاف",
        "G13": "حداثة السعر الحي",
        "G14": "صلاحية الأوامر المعلقة",
        "G15": "قفل الجلسة والتقويم",
        "G16": "فلتر الأسعار الشاذة",
        "G17": "تجميد تشغيلي للأخبار",
        "G18": "حارس الهامش",
        "G19": "الانزلاق وزمن التنفيذ",
        "G20": "ضبط حجم العقد",
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
        "followup.new_rec_blocked": (
            "A new recommendation cannot be issued yet. Active plan: {direction} — {status}.{levels} "
            "The trading kernel allows one live plan per conversation until it closes."
        ),
        "followup.plan_levels": " Entry: {entry} — Stop: {stop}.",
        "followup.one_plan_rule": "System rule: one live recommendation per conversation.",
        "followup.kernel_not_chat": (
            "This response comes from the AI trading kernel, not a static chatbot."
        ),
        "supersede.prompt": (
            "You have an active recommendation. Approve to close it and issue a new one, "
            "or reject to keep the current plan."
        ),
        "supersede.approved": "Previous recommendation closed. Issuing a new analysis…",
        "supersede.rejected": "Keeping the current active recommendation.",
        "supersede.approve_btn": "Approve new recommendation",
        "supersede.reject_btn": "Keep current plan",
        "news.warn_unknown": "Economic calendar unavailable — verify news manually before trading.",
        "direction.buy": "buy",
        "direction.sell": "sell",
        "direction.wait": "wait",
        "synth.no_usable_decision": (
            "The trading synthesizer could not produce a grounded recommendation from the evidence."
        ),
        "synth.unavailable": "Synthesizer unavailable",
        "synth.operational_blocker": "Operational blocker",
        "explain.header": "Trading kernel detail ({decision}):",
        "explain.reason": "Technical reason: {reason}",
        "explain.footer": "This answer comes from the trading kernel, not general chat.",
        "gate_report.summary": (
            "Quality checks for the live {direction} plan. Allowed: {allowed}."
        ),
        "gate_report.allowed_yes": "yes",
        "gate_report.allowed_no": "no",
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
        "gate.blocked": "Recommendation held by {check}: {reason}",
        "gate.buy_near_liquidity": "Buy entry too close to overhead liquidity ({distance})",
        "gate.sell_near_liquidity": "Sell entry too close to downside liquidity ({distance})",
        "gate.buy_against_sweep": "Buy against recent upside liquidity sweep",
        "gate.sell_against_sweep": "Sell against recent downside liquidity sweep",
        "gate.buy_in_supply": "Buy entry inside supply zone",
        "gate.sell_in_demand": "Sell entry inside demand zone",
        "display.gold": "Gold",
        "risk.settings.title": "Risk Parameters",
        "risk.settings.description": (
            "Numeric thresholds used by the gold risk and execution gates. "
            "Changes apply on the next evaluation without redeploying code."
        ),
        "risk.settings.save": "Save risk parameters",
        "risk.settings.saved": "Saved risk parameters.",
        "risk.operator_warning": (
            "Changing these values is entirely the operator's responsibility. "
            "Unsafe settings are not blocked and can increase financial exposure immediately. "
            "Human confirmation before any MT5 send cannot be disabled here."
        ),
        "risk.group.sizing": "Position sizing",
        "risk.group.drawdown": "Daily drawdown",
        "risk.group.spread": "Spread guard",
        "risk.group.cooldown": "Cooldown lock",
        "risk.group.positions": "Open positions & R:R",
        "risk.group.pending": "Pending orders & time stops",
        "risk.group.news": "News windows",
        "risk.group.execution": "Execution quality",
        "risk.group.quote": "Quote & margin",
        "risk.group.session": "Session locks",
        "risk.group.management": "Trade management",
        "risk.group.volatility": "Volatility / ADR / news candles",
        "risk.field.risk_pct_default": "Risk per trade",
        "risk.field.risk_pct_max": "Maximum risk per trade",
        "risk.field.risk_pct_news_day": "Risk on high-impact news days",
        "risk.field.daily_drawdown_pct": "Daily drawdown breaker",
        "risk.field.equity_spike_pct": "Equity spike breaker",
        "risk.field.spread_max_points": "Maximum spread",
        "risk.field.spread_stable_seconds": "Spread recovery window",
        "risk.field.spread_multiplier_pre_news": "Pre-news spread multiplier",
        "risk.field.spread_pre_news_minutes": "Pre-news spread window",
        "risk.field.cooldown_consecutive_losses": "Consecutive losses to lock",
        "risk.field.cooldown_after_two_losses_minutes": "Cooldown after consecutive losses",
        "risk.field.cooldown_after_two_losses_session_minutes": "Session cooldown after consecutive losses",
        "risk.field.cooldown_after_news_stop_minutes": "Cooldown after a news stop",
        "risk.field.max_open_gold_positions": "Maximum open gold positions (0 = no cap)",
        "risk.field.min_rr": "Minimum reward-to-risk",
        "risk.field.min_rr_live_fill": "Minimum live-fill reward-to-risk",
        "risk.field.idea_stale_hours": "Idea stale after",
        "risk.field.pending_ttl_hours": "Pending order expiry",
        "risk.field.time_stop_hours": "Time stop",
        "risk.field.half_distance_pct": "Cancel pending after this % of the target run",
        "risk.field.news_shield_minutes": "Cancel pendings this long before news",
        "risk.field.flat_near_entry_points": "Flatten if still this close to entry before news",
        "risk.field.pre_news_freeze_minutes": "Pre-news freeze window",
        "risk.field.post_news_entry_wait_minutes": "Wait after high-impact news",
        "risk.field.news_blackout_before_minutes": "News & event shield — minutes before high-impact news",
        "risk.field.news_blackout_after_minutes": "News & event shield — minutes after high-impact news",
        "risk.field.news_void_seconds": "Dead void after news release",
        "risk.field.first_minute_dead": "First-minute dead window",
        "risk.field.proposal_ttl_seconds": "HITL proposal expiry",
        "risk.field.max_confirm_slippage_points": "Confirm-time slippage cap",
        "risk.field.slippage_max_points": "Maximum expected slippage",
        "risk.field.slippage_probe_points": "Slippage probe",
        "risk.field.exec_latency_max_ms": "Maximum broker execution latency",
        "risk.field.stale_quote_seconds": "Stale quote limit",
        "risk.field.disconnect_alert_seconds": "Disconnect alert",
        "risk.field.ping_max_ms": "Maximum broker ping",
        "risk.field.bad_tick_points": "Bad-tick spike",
        "risk.field.margin_min_pct": "Minimum margin level",
        "risk.field.midnight_spread_start_hour": "Midnight-spread window start hour",
        "risk.field.midnight_spread_start_minute": "Midnight-spread window start minute",
        "risk.field.midnight_spread_end_hour": "Midnight-spread window end hour",
        "risk.field.midnight_spread_end_minute": "Midnight-spread window end minute",
        "risk.field.daily_close_lock_minutes": "Daily close lock",
        "risk.field.daily_close_hour_utc": "Daily close hour (UTC)",
        "risk.field.rollover_minute_start": "Rollover minute start",
        "risk.field.rollover_minute_end": "Rollover minute end",
        "risk.field.rollover_news_minutes": "Treat rollover as news-adjacent within",
        "risk.field.partial_tp1_pct": "Close this % at TP1",
        "risk.field.partial_tp2_pct": "Additional % at TP2",
        "risk.field.partial_tp_split_1_pct": "Staged close slice 1",
        "risk.field.partial_tp_split_2_pct": "Staged close slice 2",
        "risk.field.partial_tp_split_3_pct": "Staged close slice 3",
        "risk.field.breakeven_rr": "Move stop to breakeven at this R",
        "risk.field.profit_lock_at_target_pct": "Lock profit after this % of the run",
        "risk.field.profit_lock_keep_pct": "Keep this % of the run when locking",
        "risk.field.overnight_sl_buffer_points": "Overnight stop buffer",
        "risk.field.post_news_sl_buffer_points": "Post-news stop buffer",
        "risk.field.trail_atr_mult": "Trailing stop ATR multiple",
        "risk.field.adr_chase_multiple": "Do not chase beyond this multiple of ADR",
        "risk.field.gap_no_chase_points": "Do not chase opening gaps beyond",
        "risk.field.news_candle_atr_mult": "News-candle ATR multiple",
        "risk.field.news_candle_m1_points": "News-candle M1 range",
        "risk.field.news_candle_m5_adr_pct": "News-candle M5 as % of ADR",
        "risk.field.news_candle_volume_z": "News-candle volume z-score",
        "risk.field.atr_double_lot_halve": "Halve lot when ATR reaches this multiple",
        "risk.field.emergency_move_points_per_minute": "Emergency burst (points per minute)",
        "risk.field.max_reprice_rounds": "Live price confirmation — reprice rounds",
        "risk.field.liquidity_proximity_atr": "Liquidity proximity (ATR)",
        "risk.field.entry_max_atr_distance": "Maximum entry distance (ATR)",
        "risk.field.target_max_atr_distance": "Maximum target distance (ATR)",
        "risk.field.g7_max_slippage_atr": "Live price confirmation — re-anchor slippage (ATR)",
        "risk.field.lot_dual_check_high": "Reject lot above this multiple of sized lot",
        "risk.field.lot_dual_check_low": "Reject lot below this multiple of sized lot",
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
        "followup.new_rec_blocked": (
            "لا يمكن إصدار توصية جديدة الآن. الخطة النشطة: {direction} — {status}.{levels} "
            "نواة التداول تسمح بتوصية واحدة نشطة لكل محادثة حتى تُغلق الخطة."
        ),
        "followup.plan_levels": " الدخول: {entry} — الوقف: {stop}.",
        "followup.one_plan_rule": "قاعدة النظام: توصية واحدة نشطة لكل محادثة.",
        "followup.kernel_not_chat": (
            "هذا رد من نواة التداول الذكية (LLM + أدلة + بوابات) وليس بوتاً ثابتاً."
        ),
        "supersede.prompt": (
            "لديك توصية نشطة. وافق لإغلاقها وإصدار توصية جديدة، أو ارفض للإبقاء على الخطة الحالية."
        ),
        "supersede.approved": "تم إغلاق التوصية السابقة. جاري إصدار تحليل جديد…",
        "supersede.rejected": "تم الإبقاء على التوصية النشطة الحالية.",
        "supersede.approve_btn": "موافقة — توصية جديدة",
        "supersede.reject_btn": "رفض — الإبقاء على الحالية",
        "news.warn_unknown": "التقويم الاقتصادي غير متوفر — تحقق من الأخبار يدوياً قبل التداول.",
        "direction.buy": "شراء",
        "direction.sell": "بيع",
        "direction.wait": "انتظار",
        "synth.no_usable_decision": (
            "لم يستطع مُجمّع التداول إصدار توصية مبنية على الأدلة المتاحة."
        ),
        "synth.unavailable": "مُجمّع التداول غير متاح",
        "synth.operational_blocker": "عائق تشغيلي",
        "explain.header": "تفاصيل قرار التداول ({decision}):",
        "explain.reason": "السبب التقني: {reason}",
        "explain.footer": "هذا الرد من نواة التداول وليس محادثة عامة.",
        "gate_report.summary": (
            "فحوصات الجودة للخطة النشطة ({direction}). مسموح: {allowed}."
        ),
        "gate_report.allowed_yes": "نعم",
        "gate_report.allowed_no": "لا",
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
        "gate.blocked": "أُوقفت التوصية بواسطة {check}: {reason}",
        "gate.buy_near_liquidity": "دخول شراء قريب جداً من سيولة علوية ({distance})",
        "gate.sell_near_liquidity": "دخول بيع قريب جداً من سيولة سفلية ({distance})",
        "gate.buy_against_sweep": "شراء عكس سحب سيولة علوية حديث",
        "gate.sell_against_sweep": "بيع عكس سحب سيولة سفلية حديث",
        "gate.buy_in_supply": "دخول شراء داخل منطقة عرض",
        "gate.sell_in_demand": "دخول بيع داخل منطقة طلب",
        "display.gold": "الذهب",
        "risk.settings.title": "معاملات المخاطر",
        "risk.settings.description": (
            "عتبات رقمية تستخدمها بوابات المخاطر والتنفيذ للذهب. "
            "تُطبَّق التغييرات عند التقييم التالي دون إعادة نشر الكود."
        ),
        "risk.settings.save": "حفظ معاملات المخاطر",
        "risk.settings.saved": "تم حفظ معاملات المخاطر.",
        "risk.operator_warning": (
            "تعديل هذه القيم على مسؤولية المشغّل الكاملة. "
            "لا يُحجب الإعداد غير الآمن وقد يزيد التعرض للمخاطر المالية فوراً. "
            "لا يمكن تعطيل التأكيد البشري قبل إرسال أي أمر إلى MT5 من هنا."
        ),
        "risk.group.sizing": "حجم الصفقة",
        "risk.group.drawdown": "القطع اليومي",
        "risk.group.spread": "حارس السبريد",
        "risk.group.cooldown": "قفل التهدئة",
        "risk.group.positions": "الصفقات المفتوحة ونسبة العائد للمخاطرة",
        "risk.group.pending": "الأوامر المعلقة والوقف الزمني",
        "risk.group.news": "نوافذ الأخبار",
        "risk.group.execution": "جودة التنفيذ",
        "risk.group.quote": "التسعير والهامش",
        "risk.group.session": "أقفال الجلسة",
        "risk.group.management": "إدارة الصفقة",
        "risk.group.volatility": "التقلب / المدى اليومي / شموع الأخبار",
        "risk.field.risk_pct_default": "المخاطرة لكل صفقة",
        "risk.field.risk_pct_max": "الحد الأقصى للمخاطرة لكل صفقة",
        "risk.field.risk_pct_news_day": "المخاطرة في أيام الأخبار عالية التأثير",
        "risk.field.daily_drawdown_pct": "قاطع التراجع اليومي",
        "risk.field.equity_spike_pct": "قاطع ارتفاع حقوق الملكية",
        "risk.field.spread_max_points": "الحد الأقصى للسبريد",
        "risk.field.spread_stable_seconds": "نافذة استقرار السبريد",
        "risk.field.spread_multiplier_pre_news": "مضاعف السبريد قبل الأخبار",
        "risk.field.spread_pre_news_minutes": "نافذة السبريد قبل الأخبار",
        "risk.field.cooldown_consecutive_losses": "خسائر متتالية لتفعيل القفل",
        "risk.field.cooldown_after_two_losses_minutes": "تهدئة بعد خسائر متتالية",
        "risk.field.cooldown_after_two_losses_session_minutes": "تهدئة الجلسة بعد خسائر متتالية",
        "risk.field.cooldown_after_news_stop_minutes": "تهدئة بعد وقف بسبب الأخبار",
        "risk.field.max_open_gold_positions": "الحد الأقصى لصفقات الذهب المفتوحة (0 = بلا سقف)",
        "risk.field.min_rr": "الحد الأدنى للعائد مقابل المخاطرة",
        "risk.field.min_rr_live_fill": "الحد الأدنى للعائد مقابل المخاطرة عند التنفيذ الحي",
        "risk.field.idea_stale_hours": "تصبح الفكرة قديمة بعد",
        "risk.field.pending_ttl_hours": "انتهاء صلاحية الأمر المعلق",
        "risk.field.time_stop_hours": "الوقف الزمني",
        "risk.field.half_distance_pct": "إلغاء الأمر المعلق بعد هذه النسبة من المسار",
        "risk.field.news_shield_minutes": "إلغاء الأوامر المعلقة قبل الأخبار بهذه المدة",
        "risk.field.flat_near_entry_points": "إغلاق الصفقة إذا بقيت بهذا القرب من الدخول قبل الأخبار",
        "risk.field.pre_news_freeze_minutes": "نافذة التجميد قبل الأخبار",
        "risk.field.post_news_entry_wait_minutes": "الانتظار بعد الأخبار عالية التأثير",
        "risk.field.news_blackout_before_minutes": "درع الأخبار والأحداث — دقائق قبل الأخبار عالية التأثير",
        "risk.field.news_blackout_after_minutes": "درع الأخبار والأحداث — دقائق بعد الأخبار عالية التأثير",
        "risk.field.news_void_seconds": "الفراغ الميت بعد صدور الخبر",
        "risk.field.first_minute_dead": "نافذة الدقيقة الأولى الميتة",
        "risk.field.proposal_ttl_seconds": "انتهاء صلاحية اقتراح التأكيد البشري",
        "risk.field.max_confirm_slippage_points": "سقف الانزلاق عند التأكيد",
        "risk.field.slippage_max_points": "الحد الأقصى للانزلاق المتوقع",
        "risk.field.slippage_probe_points": "اختبار الانزلاق",
        "risk.field.exec_latency_max_ms": "الحد الأقصى لزمن تنفيذ الوسيط",
        "risk.field.stale_quote_seconds": "حد تقادم السعر",
        "risk.field.disconnect_alert_seconds": "تنبيه الانقطاع",
        "risk.field.ping_max_ms": "الحد الأقصى لنبض الوسيط",
        "risk.field.bad_tick_points": "قفزة السعر الشاذ",
        "risk.field.margin_min_pct": "الحد الأدنى لمستوى الهامش",
        "risk.field.midnight_spread_start_hour": "ساعة بداية نافذة سبريد منتصف الليل",
        "risk.field.midnight_spread_start_minute": "دقيقة بداية نافذة سبريد منتصف الليل",
        "risk.field.midnight_spread_end_hour": "ساعة نهاية نافذة سبريد منتصف الليل",
        "risk.field.midnight_spread_end_minute": "دقيقة نهاية نافذة سبريد منتصف الليل",
        "risk.field.daily_close_lock_minutes": "قفل الإغلاق اليومي",
        "risk.field.daily_close_hour_utc": "ساعة الإغلاق اليومي (UTC)",
        "risk.field.rollover_minute_start": "دقيقة بداية الرول أوفر",
        "risk.field.rollover_minute_end": "دقيقة نهاية الرول أوفر",
        "risk.field.rollover_news_minutes": "معاملة الرول أوفر كمجاور للأخبار خلال",
        "risk.field.partial_tp1_pct": "إغلاق هذه النسبة عند الهدف الأول",
        "risk.field.partial_tp2_pct": "نسبة إضافية عند الهدف الثاني",
        "risk.field.partial_tp_split_1_pct": "شريحة الإغلاق المتدرج 1",
        "risk.field.partial_tp_split_2_pct": "شريحة الإغلاق المتدرج 2",
        "risk.field.partial_tp_split_3_pct": "شريحة الإغلاق المتدرج 3",
        "risk.field.breakeven_rr": "نقل الوقف إلى التعادل عند هذا العائد",
        "risk.field.profit_lock_at_target_pct": "تثبيت الربح بعد هذه النسبة من المسار",
        "risk.field.profit_lock_keep_pct": "الإبقاء على هذه النسبة من المسار عند التثبيت",
        "risk.field.overnight_sl_buffer_points": "هامش وقف المبيت",
        "risk.field.post_news_sl_buffer_points": "هامش الوقف بعد الأخبار",
        "risk.field.trail_atr_mult": "مضاعف وقف التتبع حسب ATR",
        "risk.field.adr_chase_multiple": "عدم المطاردة بعد هذا المضاعف من المدى اليومي",
        "risk.field.gap_no_chase_points": "عدم مطاردة فجوات الافتتاح بعد",
        "risk.field.news_candle_atr_mult": "مضاعف شمعة الأخبار حسب ATR",
        "risk.field.news_candle_m1_points": "مدى شمعة الأخبار على الدقيقة",
        "risk.field.news_candle_m5_adr_pct": "شمعة الأخبار على 5 دقائق كنسبة من المدى اليومي",
        "risk.field.news_candle_volume_z": "الدرجة المعيارية لحجم شمعة الأخبار",
        "risk.field.atr_double_lot_halve": "تخفيض العقد إلى النصف عند بلوغ ATR هذا المضاعف",
        "risk.field.emergency_move_points_per_minute": "اندفاع طارئ (نقاط في الدقيقة)",
        "risk.field.max_reprice_rounds": "تأكيد السعر الحي — جولات إعادة التسعير",
        "risk.field.liquidity_proximity_atr": "قرب السيولة (ATR)",
        "risk.field.entry_max_atr_distance": "أقصى مسافة للدخول (ATR)",
        "risk.field.target_max_atr_distance": "أقصى مسافة للهدف (ATR)",
        "risk.field.g7_max_slippage_atr": "تأكيد السعر الحي — انزلاق إعادة الارتكاز (ATR)",
        "risk.field.lot_dual_check_high": "رفض العقد فوق هذا المضاعف من الحجم المحسوب",
        "risk.field.lot_dual_check_low": "رفض العقد دون هذا المضاعف من الحجم المحسوب",
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
    key = (gate_id or "").strip()
    catalog = label_map("gate", locale)
    mapped = catalog.get(key) or catalog.get(key.upper(), "")
    if mapped:
        return mapped
    if _RAW_GATE_ID.match(key):
        return ""
    return key
