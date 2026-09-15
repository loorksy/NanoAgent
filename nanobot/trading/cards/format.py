"""Gold recommendation card formatting for Telegram and WhatsApp."""

from __future__ import annotations

import html
import re
from typing import Any

from nanobot.trading.i18n import (
    BIAS_LABELS,
    DECISION_LABELS,
    DRIVER_LABELS,
    SETUP_LABELS,
    TREND_LABELS,
    label_map,
)
from nanobot.trading.locale import resolve_locale

_RR_RE = re.compile(r"R\s*:\s*R\s*([0-9]+(?:\.[0-9]+)?)", re.I)


def format_price(value: Any) -> str:
    """Format gold prices without thousands separators (LLMs misread $4,349 as $3,349)."""
    return f"${float(value):.2f}"


def _labels(locale: str) -> dict[str, str]:
    return label_map("card", locale)


def _decision_parts(payload: dict[str, Any]) -> tuple[str, str, str]:
    raw = str(payload.get("decision") or "wait").strip().lower()
    return DECISION_LABELS.get(raw, ("⚪", raw, raw.upper()))


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


def translate_reason(reason: str, *, locale: str = "en") -> str:
    loc = "ar" if locale == "ar" else "en"
    text = (reason or "").strip()
    labels = _labels(loc)
    trend_map = TREND_LABELS[loc]
    bias_map = BIAS_LABELS[loc]
    setup_map = SETUP_LABELS[loc]
    match = re.match(r"Structure trend:\s*(\w+)", text, re.I)
    if match:
        key = match.group(1).lower()
        return f"📉 {labels['trend']}: {trend_map.get(key, match.group(1))}"
    match = re.match(r"MTF bias:\s*(\w+)", text, re.I)
    if match:
        key = match.group(1).lower()
        return f"📊 {labels['bias']}: {bias_map.get(key, match.group(1))}"
    match = re.match(r"Setup:\s*(\S+)", text, re.I)
    if match:
        setup = match.group(1)
        label = setup_map.get(setup.lower(), setup.replace("_", " "))
        return f"🔻 {labels['signal']}: {label}"
    return text


def _reasons(payload: dict[str, Any], locale: str) -> list[str]:
    raw = payload.get("keyReasons") or payload.get("key_reasons") or []
    if not isinstance(raw, list):
        return []
    reasons: list[str] = []
    for item in raw[:5]:
        text = translate_reason(str(item), locale=locale)
        if text:
            reasons.append(text)
    return reasons


def _macro_driver_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("macroDrivers") or payload.get("macro_drivers") or []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def format_macro_driver_line(
    item: dict[str, Any],
    *,
    locale: str = "en",
    html_escape: bool = False,
) -> str:
    loc = "ar" if locale == "ar" else "en"
    labels = _labels(loc)
    driver_map = DRIVER_LABELS[loc]
    bias_map = BIAS_LABELS[loc]
    name = driver_map.get(str(item.get("driver") or item.get("name") or ""), "") or str(
        item.get("driver") or item.get("name") or "driver"
    )
    ran = item.get("ran")
    if ran is False:
        line = f"{name}: {labels['skipped']}"
    else:
        bias_key = str(item.get("bias") or "neutral").lower()
        bias = bias_map.get(bias_key, bias_key)
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


def _macro_section_lines(payload: dict[str, Any], *, locale: str, html_escape: bool) -> list[str]:
    rows = _macro_driver_rows(payload)
    if not rows:
        return []
    labels = _labels(locale)
    lines = ["", f"🌐 {labels['macro']}:"]
    lines.extend(
        f"• {format_macro_driver_line(item, locale=locale, html_escape=html_escape)}"
        for item in rows[:7]
    )
    return lines


def _gates_passed(payload: dict[str, Any]) -> bool | None:
    chain = payload.get("gateChain") or payload.get("gate_chain")
    if not isinstance(chain, dict):
        return None
    allowed = chain.get("allowed")
    if allowed is None:
        return None
    return bool(allowed)


def _card_locale(payload: dict[str, Any], locale: str | None) -> str:
    return resolve_locale(payload, locale=locale)


def render_telegram_card(payload: dict[str, Any], *, locale: str | None = None) -> str:
    loc = _card_locale(payload, locale)
    labels = _labels(loc)
    emoji, label_local, label_en = _decision_parts(payload)
    title = label_local if loc == "ar" else label_en
    lines = [
        f"{emoji} <b>{html.escape(labels['recommendation'])}: {html.escape(title)} ({html.escape(label_en)})</b>"
    ]
    pct = _confidence_pct(payload)
    if pct is not None:
        lines.append(f"{labels['confidence']}: {pct}%")
    rec = _recommendation(payload)
    entry = rec.get("entry")
    stop = rec.get("stopLoss") or rec.get("stop_loss")
    targets = rec.get("targets") or []
    if entry is not None or stop is not None or targets:
        lines.append("")
        if entry is not None:
            lines.append(f"🎯 {labels['entry']}: <code>{format_price(entry)}</code>")
        if stop is not None:
            lines.append(f"🛑 {labels['stop']}: <code>{format_price(stop)}</code>")
        for index, target in enumerate(targets[:2], start=1):
            lines.append(
                f"✅ {labels['target']} {index}: <code>{format_price(target)}</code>"
            )
    rr = compute_rr(payload)
    if rr is not None:
        lines.append(f"\nR:R = {rr:.2f}")
    reasons = _reasons(payload, loc)
    if reasons:
        lines.append("")
        lines.append(f"📋 {labels['reasons']}:")
        lines.extend(f"• {html.escape(reason)}" for reason in reasons)
    lines.extend(_macro_section_lines(payload, locale=loc, html_escape=True))
    gates = _gates_passed(payload)
    if gates is True:
        lines.append(f"\n✅ {labels['gates_pass']}")
    elif gates is False:
        lines.append(f"\n❌ {labels['gates_block']}")
    lines.append(f"\n<i>{html.escape(labels['disclaimer'])}</i>")
    return "\n".join(lines)


def render_whatsapp_card(payload: dict[str, Any], *, locale: str | None = None) -> str:
    loc = _card_locale(payload, locale)
    labels = _labels(loc)
    emoji, label_local, label_en = _decision_parts(payload)
    title = label_local if loc == "ar" else label_en
    lines = [f"{emoji} *{labels['recommendation']}: {title} ({label_en})*"]
    pct = _confidence_pct(payload)
    if pct is not None:
        lines.append(f"{labels['confidence']}: {pct}%")
    rec = _recommendation(payload)
    entry = rec.get("entry")
    stop = rec.get("stopLoss") or rec.get("stop_loss")
    targets = rec.get("targets") or []
    if entry is not None or stop is not None or targets:
        lines.append("")
        if entry is not None:
            lines.append(f"🎯 {labels['entry']}: {format_price(entry)}")
        if stop is not None:
            lines.append(f"🛑 {labels['stop']}: {format_price(stop)}")
        for index, target in enumerate(targets[:2], start=1):
            lines.append(f"✅ {labels['target']} {index}: {format_price(target)}")
    rr = compute_rr(payload)
    if rr is not None:
        lines.append(f"\nR:R = {rr:.2f}")
    reasons = _reasons(payload, loc)
    if reasons:
        lines.append("")
        lines.append(f"📋 {labels['reasons']}:")
        lines.extend(f"• {reason}" for reason in reasons)
    lines.extend(_macro_section_lines(payload, locale=loc, html_escape=False))
    gates = _gates_passed(payload)
    if gates is True:
        lines.append(f"\n✅ {labels['gates_pass']}")
    elif gates is False:
        lines.append(f"\n❌ {labels['gates_block']}")
    emphasis = "_" if loc == "ar" else "_"
    lines.append(f"\n{emphasis}{labels['disclaimer']}{emphasis}")
    return "\n".join(lines)
