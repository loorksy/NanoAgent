"""Normalized gate check result used by G8+ modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from nanobot.trading.i18n import tr

GateCheckStatus = Literal["pass", "veto", "unavailable", "warn"]


def _format_params(evidence: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in evidence.items() if type(value) in (str, int, float)}


@dataclass(frozen=True)
class GateCheck:
    status: GateCheckStatus
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence_delta: int = 0
    reason_key: str = ""
    reason_params: dict[str, Any] = field(default_factory=dict)

    def as_raw(self) -> dict[str, Any]:
        key = self.reason_key
        params = dict(self.reason_params)
        reason = tr(key, **params) if key else self.reason
        reason_ar = tr(key, "ar", **params) if key else ""
        raw: dict[str, Any] = {
            "status": self.status,
            "reason": reason,
            "reason_key": key,
            "reason_params": params,
            "reason_ar": reason_ar,
        }
        if self.evidence:
            raw["evidence"] = self.evidence
        if self.confidence_delta:
            raw["confidence_delta"] = self.confidence_delta
        return raw


def passed(**evidence: Any) -> GateCheck:
    return GateCheck("pass", evidence=dict(evidence) if evidence else {})


def veto(key: str, **evidence: Any) -> GateCheck:
    params = _format_params(evidence)
    return GateCheck(
        "veto",
        reason=tr(key, **params),
        evidence=dict(evidence) if evidence else {},
        reason_key=key,
        reason_params=params,
    )


def unavailable(key: str, **evidence: Any) -> GateCheck:
    params = _format_params(evidence)
    return GateCheck(
        "unavailable",
        reason=tr(key, **params),
        evidence=dict(evidence) if evidence else {},
        reason_key=key,
        reason_params=params,
    )


def warn(key: str, delta: int = 0, **evidence: Any) -> GateCheck:
    params = _format_params(evidence)
    return GateCheck(
        "warn",
        reason=tr(key, **params),
        evidence=dict(evidence) if evidence else {},
        confidence_delta=delta,
        reason_key=key,
        reason_params=params,
    )


def disabled_by_operator(toggle: str) -> GateCheck:
    """Operator turned this named protection off. Not a silent pass."""
    return GateCheck(
        "pass",
        reason=tr("gate.disabled_by_operator", toggle=toggle),
        evidence={"disabled_by_operator": True, "toggle": toggle},
        reason_key="gate.disabled_by_operator",
        reason_params={"toggle": toggle},
    )
