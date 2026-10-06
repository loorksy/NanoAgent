"""FEATURE-05 — zero-latency regex emergency engine."""

from __future__ import annotations

from dataclasses import dataclass

from mokli.trading.intel import lexicon
from mokli.trading.risk_state import get_risk_store

WAR = lexicon.alternation("emergency_war")
MONETARY = lexicon.alternation("emergency_monetary")
SANCTIONS = lexicon.alternation("emergency_sanctions")


@dataclass(frozen=True)
class EmergencyHit:
    matched: bool
    category: str
    pattern: str
    text: str

    @property
    def freeze(self) -> bool:
        return self.matched and self.category in {"war", "monetary"}


def scan_emergency(text: str, *, apply_lock: bool = False) -> EmergencyHit:
    if WAR.search(text):
        hit = EmergencyHit(True, "war", WAR.pattern, text)
    elif MONETARY.search(text):
        hit = EmergencyHit(True, "monetary", MONETARY.pattern, text)
    elif SANCTIONS.search(text):
        hit = EmergencyHit(True, "sanctions", SANCTIONS.pattern, text)
    else:
        hit = EmergencyHit(False, "", "", text)
    if hit.freeze and apply_lock:
        get_risk_store().update(emergency_lock=True)
    return hit
