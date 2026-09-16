"""Normalized gate check result used by G8+ modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

GateCheckStatus = Literal["pass", "veto", "unavailable", "warn"]


@dataclass(frozen=True)
class GateCheck:
    status: GateCheckStatus
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence_delta: int = 0

    def as_raw(self) -> dict[str, Any]:
        raw: dict[str, Any] = {"status": self.status, "reason_ar": self.reason}
        if self.evidence:
            raw["evidence"] = self.evidence
        if self.confidence_delta:
            raw["confidence_delta"] = self.confidence_delta
        return raw


def passed(**evidence: Any) -> GateCheck:
    return GateCheck("pass", evidence=dict(evidence) if evidence else {})


def veto(reason: str, **evidence: Any) -> GateCheck:
    return GateCheck("veto", reason=reason, evidence=dict(evidence) if evidence else {})


def unavailable(reason: str, **evidence: Any) -> GateCheck:
    return GateCheck("unavailable", reason=reason, evidence=dict(evidence) if evidence else {})


def warn(reason: str, delta: int = 0, **evidence: Any) -> GateCheck:
    return GateCheck(
        "warn",
        reason=reason,
        evidence=dict(evidence) if evidence else {},
        confidence_delta=delta,
    )
