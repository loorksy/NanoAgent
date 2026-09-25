"""Output policy rewrites use catalog text for both scripts."""

from __future__ import annotations

from nanobot.trading.i18n import tr
from nanobot.trading.output_policy import apply_output_policy
from nanobot.trading.turn_session import TurnSession, turn_session_scope


def test_arabic_sides_are_rewritten_from_catalog() -> None:
    rewritten = apply_output_policy("توصية: شراء الذهب الآن", mutate=True)
    assert tr("direction.buy", "ar") not in rewritten
    assert tr("output_policy.no_recommendation", "ar") in rewritten


def test_authorized_buy_turns_arabic_sell_into_wait() -> None:
    session = TurnSession()
    session.kernel_ran = True
    session.kernel_decision = "buy"
    with turn_session_scope(session):
        rewritten = apply_output_policy("شراء ثم بيع", mutate=True)
    assert tr("direction.buy", "ar") in rewritten
    assert tr("direction.sell", "ar") not in rewritten
    assert tr("direction.wait", "ar") in rewritten


def test_price_placeholder_and_quality_check_come_from_catalog() -> None:
    rewritten = apply_output_policy("G7 says 2500", mutate=True)
    assert tr("output_policy.price_placeholder", "en") in rewritten
    assert tr("output_policy.quality_check", "en") in rewritten
    assert "G7" not in rewritten
