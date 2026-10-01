"""Every team role file has display copy, and the gold review roles use it."""

from __future__ import annotations

from mokli.agent.prompt.composer import team_role_names
from mokli.trading.teams.role_display import ROLE_DISPLAY, role_phrase


def test_every_role_file_has_display_copy() -> None:
    missing = [name for name in team_role_names() if name not in ROLE_DISPLAY]
    assert missing == []
    for phases in ROLE_DISPLAY.values():
        assert len(phases) == 3
        assert all(phases)


def test_gold_review_roles_use_their_file_phrase() -> None:
    assert role_phrase("Technical Analyst", "running", system_prompt="role:structure").startswith(
        "يراجع الهيكل"
    )
    assert role_phrase("Trend Analyst", "done", system_prompt="role:timeframe").startswith(
        "اكتملت مراجعة الاتجاه"
    )
    assert role_phrase("Macro News Analyst", "running", system_prompt="role:macro").startswith(
        "يراجع الأخبار"
    )
    assert role_phrase("Risk Officer", "failed", system_prompt="role:risk").startswith(
        "تعذرت مراجعة المخاطر"
    )
    assert role_phrase("Review Analyst", "done", system_prompt="role:lead").startswith(
        "اكتملت المراجعة"
    )
    phrase = role_phrase("Technical Analyst", "running", system_prompt="role:structure")
    assert "Technical Analyst" not in phrase
