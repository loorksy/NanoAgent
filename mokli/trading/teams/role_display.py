"""Human phrases for trading-team roles.

The chat surface reads these strings from the role event. It does not branch
on the role label. A role file missing from ``ROLE_DISPLAY`` fails the catalog
test. An unknown label at runtime uses ``GENERIC``.
"""

from __future__ import annotations

from mokli.trading.teams.role_prompts import resolve_role_file

_Phase = tuple[str, str, str]

GENERIC: _Phase = (
    "يعمل متخصص…",
    "اكتمل عمل المتخصص",
    "تعذر عمل المتخصص",
)

ROLE_DISPLAY: dict[str, _Phase] = {
    "structure": ("يراجع الهيكل السعري…", "اكتملت مراجعة الهيكل", "تعذرت مراجعة الهيكل"),
    "timeframe": ("يراجع الاتجاه عبر الإطارات…", "اكتملت مراجعة الاتجاه", "تعذرت مراجعة الاتجاه"),
    "macro": ("يراجع الأخبار والاقتصاد…", "اكتملت مراجعة الأخبار", "تعذرت مراجعة الأخبار"),
    "news": ("يراجع الأخبار…", "اكتملت مراجعة الأخبار", "تعذرت مراجعة الأخبار"),
    "risk": ("يراجع المخاطر…", "اكتملت مراجعة المخاطر", "تعذرت مراجعة المخاطر"),
    "lead": ("يراجع آراء الفريق…", "اكتملت المراجعة", "تعذرت المراجعة"),
    "liquidity": ("يراجع السيولة…", "اكتملت مراجعة السيولة", "تعذرت مراجعة السيولة"),
    "scenario": ("يراجع السيناريوهات…", "اكتملت مراجعة السيناريوهات", "تعذرت مراجعة السيناريوهات"),
    "bull": ("يراجع سيناريو الصعود…", "اكتملت مراجعة الصعود", "تعذرت مراجعة الصعود"),
    "bear": ("يراجع سيناريو الهبوط…", "اكتملت مراجعة الهبوط", "تعذرت مراجعة الهبوط"),
    "mtf_synthesizer": ("يراجع الإطارات الزمنية…", "اكتملت مراجعة الإطارات", "تعذرت مراجعة الإطارات"),
    "event": ("يراجع الأحداث الاقتصادية…", "اكتملت مراجعة الأحداث", "تعذرت مراجعة الأحداث"),
}


def role_phrase(role: str, status: str, *, system_prompt: str = "") -> str:
    """Phrase for one role that is actually running, done, or failed."""
    phases = ROLE_DISPLAY.get(resolve_role_file(role, system_prompt), GENERIC)
    if status in {"done", "finished", "completed"}:
        return phases[1]
    if status in {"failed", "error"}:
        return phases[2]
    return phases[0]
