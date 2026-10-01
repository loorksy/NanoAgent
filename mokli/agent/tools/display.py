"""Human display copy for tools.

The chat surface reads these phrases. It does not branch on tool names.
A tool missing from ``DISPLAY`` still runs, and the surface uses ``GENERIC``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolDisplay:
    started: str
    running: str
    completed: str
    failed: str
    waiting: str = "جاري المعالجة…"


GENERIC = ToolDisplay(
    started="ينفّذ خطوة",
    running="ينفّذ خطوة",
    completed="اكتملت الخطوة",
    failed="تعذرت الخطوة",
)


def _copy(started: str, completed: str, failed: str, *, running: str | None = None) -> ToolDisplay:
    return ToolDisplay(
        started=started,
        running=running or started,
        completed=completed,
        failed=failed,
    )


DISPLAY: dict[str, ToolDisplay] = {
    "get_gold_quote": _copy(
        "يفحص سعر الذهب الحالي…",
        "تم فحص سعر الذهب",
        "تعذر الحصول على سعر الذهب",
    ),
    "get_live_recommendation": _copy(
        "يراجع التوصية الحية…",
        "اكتملت مراجعة التوصية",
        "تعذرت مراجعة التوصية",
    ),
    "manage_trading_plan": _copy(
        "يراجع خطة التداول…",
        "اكتملت مراجعة الخطة",
        "تعذرت مراجعة الخطة",
    ),
    "analyze_gold": _copy(
        "يحلّل الذهب…",
        "اكتمل تحليل الذهب",
        "تعذر تحليل الذهب",
    ),
    "capture_gold_chart": _copy(
        "يلتقط الرسم البياني…",
        "تم التقاط الرسم",
        "تعذر التقاط الرسم",
    ),
    "fetch_evidence": _copy(
        "يجمع أدلة السوق…",
        "اكتمل جمع الأدلة",
        "تعذر جمع الأدلة",
    ),
    "run_trading_kernel": _copy(
        "يشغّل محرك التحليل",
        "اكتمل تشغيل محرك التحليل",
        "تعذر تشغيل محرك التحليل",
    ),
    "get_gate_report": _copy(
        "يتحقق من شروط القرار…",
        "اكتمل فحص شروط القرار",
        "تعذر فحص شروط القرار",
    ),
    "run_trading_team": _copy(
        "يشغّل فريق التحليل…",
        "اكتمل عمل فريق التحليل",
        "تعذر تشغيل فريق التحليل",
    ),
    "gold_intel_scan": _copy(
        "يفحص الأخبار والاقتصاد…",
        "اكتمل فحص الأخبار",
        "تعذر فحص الأخبار",
    ),
    "fast_backtest": _copy(
        "يختبر الاستراتيجية على البيانات السابقة…",
        "اكتمل الاختبار التاريخي",
        "تعذر الاختبار التاريخي",
    ),
    "propose_strategy": _copy(
        "يصوغ مواصفات الاستراتيجية…",
        "اكتملت مواصفات الاستراتيجية",
        "تعذر صياغة المواصفات",
    ),
    "web_search": _copy(
        "يبحث في الويب…",
        "اكتمل البحث",
        "تعذر البحث",
    ),
    "web_fetch": _copy(
        "يقرأ الصفحة…",
        "اكتملت قراءة الصفحة",
        "تعذرت قراءة الصفحة",
    ),
    "spawn": _copy(
        "يشغّل وكيلاً متخصصاً…",
        "انتهى الوكيل المتخصص",
        "تعذر تشغيل الوكيل المتخصص",
    ),
    "message": _copy(
        "يرسل رسالة…",
        "أُرسلت الرسالة",
        "تعذر إرسال الرسالة",
    ),
    "cron": _copy(
        "يراجع المهام المجدولة…",
        "اكتملت مراجعة المهام",
        "تعذرت مراجعة المهام",
    ),
    "list_sessions": _copy(
        "يستعرض الجلسات…",
        "اكتمل استعراض الجلسات",
        "تعذر استعراض الجلسات",
    ),
    "search_sessions": _copy(
        "يبحث في الجلسات…",
        "اكتمل البحث في الجلسات",
        "تعذر البحث في الجلسات",
    ),
    "read_session": _copy(
        "يقرأ جلسة سابقة…",
        "اكتملت قراءة الجلسة",
        "تعذرت قراءة الجلسة",
    ),
    "send_session_message": _copy(
        "يرسل رسالة إلى جلسة…",
        "أُرسلت الرسالة إلى الجلسة",
        "تعذر إرسال الرسالة إلى الجلسة",
    ),
    "create_goal": _copy(
        "يسجّل هدفاً…",
        "سُجّل الهدف",
        "تعذر تسجيل الهدف",
    ),
    "update_goal": _copy(
        "يحدّث الهدف…",
        "اكتمل تحديث الهدف",
        "تعذر تحديث الهدف",
    ),
    "mt5_list_symbols": _copy(
        "يراجع رموز الحساب…",
        "اكتملت مراجعة الرموز",
        "تعذرت مراجعة الرموز",
    ),
    "mt5_market": _copy(
        "يقرأ بيانات الحساب…",
        "اكتملت قراءة بيانات الحساب",
        "تعذرت قراءة بيانات الحساب",
    ),
    "mt5_get_account": _copy(
        "يراجع حالة الحساب…",
        "اكتملت مراجعة الحساب",
        "تعذرت مراجعة الحساب",
    ),
    "mt5_propose_order": _copy(
        "يجهّز اقتراح أمر…",
        "جُهّز اقتراح الأمر",
        "تعذر تجهيز اقتراح الأمر",
    ),
    "mt5_confirm_order": _copy(
        "ينفّذ الأمر بعد الموافقة…",
        "اكتمل مسار الأمر",
        "تعذر تنفيذ الأمر",
    ),
    "mt5_modify_order": _copy(
        "يعدّل الأمر…",
        "اكتمل تعديل الأمر",
        "تعذر تعديل الأمر",
    ),
    "mt5_close_position": _copy(
        "يغلق الصفقة…",
        "أُغلقت الصفقة",
        "تعذر إغلاق الصفقة",
    ),
    "mt5_cancel_order": _copy(
        "يلغي الأمر المعلّق…",
        "أُلغي الأمر",
        "تعذر إلغاء الأمر",
    ),
}


def explicit_display(name: str) -> ToolDisplay | None:
    return DISPLAY.get(name)


def display_for(name: str) -> ToolDisplay:
    return DISPLAY.get(name) or GENERIC


def phrase_for(name: str, phase: str) -> str:
    spec = display_for(name)
    if phase in {"finished", "completed"}:
        return spec.completed
    if phase == "failed":
        return spec.failed
    if phase == "running":
        return spec.running
    if phase == "waiting":
        return spec.waiting
    return spec.started
