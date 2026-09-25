"""Output policy — strip unauthorized BUY/SELL and unverified prices.

Always returns a chat reply. Never a gateway crash.
"""

from __future__ import annotations

import re

from nanobot.trading.i18n import tr
from nanobot.trading.turn_session import current_turn_session

_SIDE_EN = re.compile(r"\b(buy|sell|long|short)\b", re.I)
_SIDE_AR = re.compile(
    "(" + "|".join(re.escape(tr(key, "ar")) for key in ("direction.buy", "direction.sell")) + ")"
)
_PRICE_TOKEN = re.compile(r"\b\d{3,5}(?:\.\d{1,2})?\b")
_OPAQUE_IDS = re.compile(r"\b(G(?:[1-9]|1[0-9]|20)|OANDA)\b")


def _placeholder() -> str:
    return tr("output_policy.price_placeholder", "en")


def _authorized_side() -> str | None:
    turn = current_turn_session()
    if turn is None or not turn.kernel_ran:
        return None
    decision = (turn.kernel_decision or "").strip().lower()
    if decision in {"buy", "sell"}:
        return decision
    return None


def _rewrite_sides(text: str) -> str:
    allowed = _authorized_side()
    wait_en = tr("direction.wait", "en")
    wait_ar = tr("direction.wait", "ar")
    if allowed == "buy":
        text = re.sub(r"\b(sell|short)\b", wait_en, text, flags=re.I)
        return text.replace(tr("direction.sell", "ar"), wait_ar)
    if allowed == "sell":
        text = re.sub(r"\b(buy|long)\b", wait_en, text, flags=re.I)
        return text.replace(tr("direction.buy", "ar"), wait_ar)
    replaced = _SIDE_EN.sub(tr("output_policy.no_recommendation", "en"), text)
    replaced = _SIDE_AR.sub(tr("output_policy.no_recommendation", "ar"), replaced)
    return replaced


def _rewrite_prices(text: str) -> str:
    turn = current_turn_session()
    allowed = set(turn.authorized_prices) if turn is not None else set()
    placeholder = _placeholder()
    if not allowed:
        return _PRICE_TOKEN.sub(placeholder, text)

    def _keep_or_drop(match: re.Match[str]) -> str:
        token = match.group(0)
        if token in allowed:
            return token
        return placeholder

    return _PRICE_TOKEN.sub(_keep_or_drop, text)


def _scrub_opaque_ids(text: str) -> str:
    return _OPAQUE_IDS.sub(tr("output_policy.quality_check", "en"), text)


def apply_output_policy(assistant_text: str, *, mutate: bool = True) -> str:
    text = assistant_text or ""
    if not mutate:
        return text
    return _scrub_opaque_ids(_rewrite_prices(_rewrite_sides(text)))
