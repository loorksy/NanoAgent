"""Operator input keywords for intent routing (detection only — not user-facing copy)."""

from __future__ import annotations

import re

# Arabic phrases use formal forms where operators may type them; kept separate from i18n output.
EXPLICIT_NEW_ANALYSIS_PHRASES: tuple[str, ...] = (
    "analyze",
    "analyse",
    "reanalyze",
    "re-analyze",
    "new recommendation",
    "another recommendation",
    "fresh analysis",
    "give me a recommendation",
    # operator input (detection only)
    "حلل",
    "حلّل",
    "تحليل جديد",
    "توصية جديدة",
    "فرصة جديدة",
    "صفقة جديدة",
    "أعطني توصية",
    "اعطني توصية",
    "اعطيني توصية",
    "أريد توصية",
    "اريد توصية",
)

_PRICE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(price|quote|bid|ask)\b", re.I),
    re.compile(r"(سعر|كم السعر|كم سعر)", re.I),
)
_ANALYSIS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(analy[sz]e|analysis|outlook|setup)\b", re.I),
    re.compile(r"(حلل|حلّل|تحليل|تحليل الذهب)", re.I),
)
_RECOMMEND_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(recommend|recommendation|buy|sell|trade idea)\b", re.I),
    re.compile(r"(توصية|شراء|بيع|صفقة)", re.I),
)
_GOLD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(xauusd|xau/usd|gold)\b", re.I),
    re.compile(r"(ذهب|الذهب)", re.I),
)
_TEAM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(committee|debate desk|war room|mtf panel|swarm team)\b", re.I),
    re.compile(r"(فريق التحليل|لجنة الذهب|غرفة الأخبار)", re.I),
)
_CHART_IMAGE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(chart|screenshot|screen\s*shot|snapshot|capture)\b", re.I),
    re.compile(r"(صورة|لقطة|رسم بياني|الرسم البياني)", re.I),
)

_PRESET_BY_KEYWORD: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(war room|غرفة الأخبار)", re.I), "gold_news_war_room"),
    (re.compile(r"(debate desk|مناظرة)", re.I), "gold_debate_desk"),
    (re.compile(r"(mtf panel|لوحة الأطر)", re.I), "gold_mtf_panel"),
    (re.compile(r"(committee|لجنة)", re.I), "gold_analysis_committee"),
)

_LEVEL_KEYWORDS = re.compile(
    r"\b(entry|stop|target|tp|sl|levels?)\b|"
    r"(دخل|نقطة الدخول|وقف|وقف الخسارة|هدف|أهداف|مستويات)",
    re.I,
)
_STATUS_KEYWORDS = re.compile(
    r"\b(status|still|active|alive|outcome)\b|"
    r"(حالة|ما زال|ساري|نشط|أين وصل|الوضع الحالي)",
    re.I,
)
_GATE_KEYWORDS = re.compile(
    r"\b(gate|block|veto|blocked)\b|(بواب|حظر|رفض|محجوب)",
    re.I,
)

_FOLLOWUP_NEW_REC_MARKERS = re.compile(
    r"(توصية جديدة|حلل|حلّل|recommend|analy)", re.I,
)
