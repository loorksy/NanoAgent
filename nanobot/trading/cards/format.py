"""Arabic-first gold recommendation card formatting for Telegram and WhatsApp."""

from __future__ import annotations

import html
import re
from typing import Any

_RR_RE = re.compile(r"R\s*:\s*R\s*([0-9]+(?:\.[0-9]+)?)", re.I)
_TREND_AR = {
    "up": "صاعد",
    "down": "هابط",
    "bullish": "صاعد",
    "bearish": "هابط",
    "neutral": "محايد",
    "sideways": "عرضي",
    "range": "عرضي",
}
_BIAS_AR = {
    "up": "صعودي",
    "down": "هبوطي",
    "bullish": "صعودي",
    "bearish": "هبوطي",
    "neutral": "محايد",
    "sideways": "عرضي",
    "range": "عرضي",
}
_SETUP_AR = {
    "structure_break": "كسر هيكل",
    "structure": "هيكل",
    "breakout": "اختراق",
    "supply": "منطقة عرض",
    "demand": "منطقة طلب",
    "liquidity_sweep": "كنس سيولة",
}
_DECISION = {
    "buy": ("🟢", "شراء", "BUY"),
    "sell": ("🔴", "بيع", "SELL"),
    "wait": ("⚪", "انتظار", "WAIT"),
}
_DRIVER_AR = {
    "geopolitical_safehaven": "ملاذ جيوسياسي",
    "dxy": "الدولار",
    "us_macro_data": "بيانات أمريكية",
    "us_real_yields_fomc": "العوائد / الفيدرالي",
    "fund_flows_positioning": "تدفقات الصناديق",
    "central_bank_demand": "طلب البنوك المركزية",
    "seasonal_physical_demand": "الطلب الموسمي",
}


def format_price(value: Any) -> str:
    return f"${float(value):,.2f}"


def _decision_parts(payload: dict[str, Any]) -> tuple[str, str, str]:
    raw = str(payload.get("decision") or "wait").strip().lower()
    return _DECISION.get(raw, ("⚪", raw, raw.upper()))


def _confidence_pct(payload: dict[str, Any]) -> int | None:
    confidence = payload.get("confidence")
    if confidence is None:
        return None
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return None
    if value <= 1:
        value *= 100
    return int(round(value))


def _recommendation(payload: dict[str, Any]) -> dict[str, Any]:
    rec = payload.get("recommendation")
    return rec if isinstance(rec, dict) else {}


def compute_rr(payload: dict[str, Any]) -> float | None:
    rec = _recommendation(payload)
    entry = rec.get("entry")
    stop = rec.get("stopLoss") or rec.get("stop_loss")
    targets = rec.get("targets") or []
    match = _RR_RE.search(str(payload.get("summary") or ""))
    if match:
        return float(match.group(1))
    if entry is not None and stop is not None and targets:
        risk = abs(float(entry) - float(stop))
        if risk > 0:
            reward = max(abs(float(target) - float(entry)) for target in targets[:2])
            return reward / risk
    return None


def translate_reason(reason: str) -> str:
    text = (reason or "").strip()
    match = re.match(r"Structure trend:\s*(\w+)", text, re.I)
    if match:
        key = match.group(1).lower()
        return f"📉 الاتجاه: {_TREND_AR.get(key, match.group(1))}"
    match = re.match(r"MTF bias:\s*(\w+)", text, re.I)
    if match:
        key = match.group(1).lower()
        return f"📊 التحيز: {_BIAS_AR.get(key, match.group(1))}"
    match = re.match(r"Setup:\s*(\S+)", text, re.I)
    if match:
        setup = match.group(1)
        label = _SETUP_AR.get(setup.lower(), setup.replace("_", " "))
        return f"🔻 إشارة: {label}"
    return text


def _reasons(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("keyReasons") or payload.get("key_reasons") or []
    if not isinstance(raw, list):
        return []
    reasons: list[str] = []
    for item in raw[:5]:
        text = translate_reason(str(item))
        if text:
            reasons.append(text)
    return reasons


def _macro_driver_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("macroDrivers") or payload.get("macro_drivers") or []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def format_macro_driver_line(item: dict[str, Any], *, html_escape: bool = False) -> str:
    name = _DRIVER_AR.get(str(item.get("driver") or item.get("name") or ""), "") or str(
        item.get("driver") or item.get("name") or "driver"
    )
    ran = item.get("ran")
    if ran is False:
        line = f"{name}: تخطى — كاش/غير ذي صلة"
    else:
        bias_key = str(item.get("bias") or "neutral").lower()
        bias = _BIAS_AR.get(bias_key, bias_key)
        strength = item.get("strength")
        try:
            strength_txt = str(int(strength))
        except (TypeError, ValueError):
            strength_txt = "—"
        rationale = str(item.get("one_line_rationale") or "").strip()
        line = f"{name}: {bias} {strength_txt}"
        if rationale:
            line = f"{line} — {rationale}"
    return html.escape(line) if html_escape else line


def _macro_section_lines(payload: dict[str, Any], *, html_escape: bool) -> list[str]:
    rows = _macro_driver_rows(payload)
    if not rows:
        return []
    lines = ["", "🌐 محركات الاقتصاد الكلي:"]
    lines.extend(f"• {format_macro_driver_line(item, html_escape=html_escape)}" for item in rows[:7])
    return lines


def _gates_passed(payload: dict[str, Any]) -> bool | None:
    chain = payload.get("gateChain") or payload.get("gate_chain")
    if not isinstance(chain, dict):
        return None
    allowed = chain.get("allowed")
    if allowed is None:
        return None
    return bool(allowed)


def render_telegram_card(payload: dict[str, Any]) -> str:
    emoji, label_ar, label_en = _decision_parts(payload)
    lines = [f"{emoji} <b>توصية: {html.escape(label_ar)} ({html.escape(label_en)})</b>"]
    pct = _confidence_pct(payload)
    if pct is not None:
        lines.append(f"الثقة: {pct}%")
    rec = _recommendation(payload)
    entry = rec.get("entry")
    stop = rec.get("stopLoss") or rec.get("stop_loss")
    targets = rec.get("targets") or []
    if entry is not None or stop is not None or targets:
        lines.append("")
        if entry is not None:
            lines.append(f"🎯 الدخول: <code>{format_price(entry)}</code>")
        if stop is not None:
            lines.append(f"🛑 وقف الخسارة: <code>{format_price(stop)}</code>")
        for index, target in enumerate(targets[:2], start=1):
            lines.append(f"✅ الهدف {index}: <code>{format_price(target)}</code>")
    rr = compute_rr(payload)
    if rr is not None:
        lines.append(f"\nR:R = {rr:.2f}")
    reasons = _reasons(payload)
    if reasons:
        lines.append("")
        lines.append("📋 الأسباب:")
        lines.extend(f"• {html.escape(reason)}" for reason in reasons)
    lines.extend(_macro_section_lines(payload, html_escape=True))
    gates = _gates_passed(payload)
    if gates is True:
        lines.append("\n✅ جميع البوابات (G1-G7) ناجحة")
    elif gates is False:
        lines.append("\n❌ التوصية محجوبة من بوابات المخاطر")
    lines.append("\n<i>توصيات فقط — بدون تنفيذ.</i>")
    return "\n".join(lines)


def render_whatsapp_card(payload: dict[str, Any]) -> str:
    emoji, label_ar, label_en = _decision_parts(payload)
    lines = [f"{emoji} *توصية: {label_ar} ({label_en})*"]
    pct = _confidence_pct(payload)
    if pct is not None:
        lines.append(f"الثقة: {pct}%")
    rec = _recommendation(payload)
    entry = rec.get("entry")
    stop = rec.get("stopLoss") or rec.get("stop_loss")
    targets = rec.get("targets") or []
    if entry is not None or stop is not None or targets:
        lines.append("")
        if entry is not None:
            lines.append(f"🎯 الدخول: {format_price(entry)}")
        if stop is not None:
            lines.append(f"🛑 وقف الخسارة: {format_price(stop)}")
        for index, target in enumerate(targets[:2], start=1):
            lines.append(f"✅ الهدف {index}: {format_price(target)}")
    rr = compute_rr(payload)
    if rr is not None:
        lines.append(f"\nR:R = {rr:.2f}")
    reasons = _reasons(payload)
    if reasons:
        lines.append("")
        lines.append("📋 الأسباب:")
        lines.extend(f"• {reason}" for reason in reasons)
    lines.extend(_macro_section_lines(payload, html_escape=False))
    gates = _gates_passed(payload)
    if gates is True:
        lines.append("\n✅ جميع البوابات (G1-G7) ناجحة")
    elif gates is False:
        lines.append("\n❌ التوصية محجوبة من بوابات المخاطر")
    lines.append("\n_توصيات فقط — بدون تنفيذ._")
    return "\n".join(lines)
