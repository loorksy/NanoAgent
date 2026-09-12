"""Route user messages to gold trading modes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

IntentKind = Literal[
    "price_query",
    "gold_analysis",
    "recommendation",
    "team_swarm",
    "general_chat",
]

_PRICE_PATTERNS = (
    re.compile(r"\b(price|quote|bid|ask)\b", re.I),
    re.compile(r"(سعر|كم السعر|كم سعر)", re.I),
)
_ANALYSIS_PATTERNS = (
    re.compile(r"\b(analy[sz]e|analysis|outlook|setup)\b", re.I),
    re.compile(r"(حلل|تحليل|شوف الذهب|تحليل الذهب)", re.I),
)
_RECOMMEND_PATTERNS = (
    re.compile(r"\b(recommend|recommendation|buy|sell|trade idea)\b", re.I),
    re.compile(r"(توصية|توصيه|شراء|بيع|صفقة)", re.I),
)
_GOLD_PATTERNS = (
    re.compile(r"\b(xauusd|xau/usd|gold)\b", re.I),
    re.compile(r"(ذهب|الذهب)", re.I),
)
_TEAM_PATTERNS = (
    re.compile(r"\b(committee|debate desk|war room|mtf panel|swarm team)\b", re.I),
    re.compile(r"(فريق التحليل|لجنة الذهب|غرفة الأخبار|شغّل الفريق)", re.I),
)


@dataclass(frozen=True)
class RoutedIntent:
    kind: IntentKind
    confidence: float
    reason: str


_PRESET_BY_KEYWORD: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(war room|غرفة الأخبار)", re.I), "gold_news_war_room"),
    (re.compile(r"(debate desk|مناظرة)", re.I), "gold_debate_desk"),
    (re.compile(r"(mtf panel|لوحة)", re.I), "gold_mtf_panel"),
    (re.compile(r"(committee|لجنة)", re.I), "gold_analysis_committee"),
)


def resolve_team_preset(message: str) -> str | None:
    text = (message or "").strip()
    if not text:
        return None
    for pattern, preset in _PRESET_BY_KEYWORD:
        if pattern.search(text):
            return preset
    return None


def route_intent(message: str) -> RoutedIntent:
    text = (message or "").strip()
    if not text:
        return RoutedIntent("general_chat", 0.0, "empty")

    mentions_gold = any(p.search(text) for p in _GOLD_PATTERNS)
    if any(p.search(text) for p in _TEAM_PATTERNS):
        return RoutedIntent("team_swarm", 0.9 if mentions_gold else 0.75, "team preset keywords")
    if any(p.search(text) for p in _RECOMMEND_PATTERNS):
        return RoutedIntent("recommendation", 0.9 if mentions_gold else 0.85, "recommendation keywords")
    if any(p.search(text) for p in _ANALYSIS_PATTERNS):
        return RoutedIntent("gold_analysis", 0.9 if mentions_gold else 0.85, "analysis keywords")
    if any(p.search(text) for p in _PRICE_PATTERNS):
        return RoutedIntent("price_query", 0.85 if mentions_gold else 0.6, "price keywords")
    if mentions_gold:
        return RoutedIntent("gold_analysis", 0.65, "gold mention")
    return RoutedIntent("general_chat", 0.5, "default")
