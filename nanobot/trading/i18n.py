"""Central trading message catalog — thin loader over ``locales/{ar,en}.json``.

All user-facing copy (professional Arabic + English) lives in the flat JSON
catalogs. Label groups are namespaced as ``label.<group>.<item>``; message
templates keep their dotted keys (``price.header``, ``gate.blocked``, …).
"""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import Any, cast

from nanobot.trading.locale import normalize_locale

_RAW_GATE_ID = re.compile(r"^G\d+$", re.I)
_LOCALES_DIR = Path(__file__).resolve().parent / "locales"
_LABEL_PREFIX = "label."
SUPPORTED_LOCALES: tuple[str, ...] = ("en", "ar")


@cache
def _load_catalog(locale: str) -> dict[str, str]:
    path = _LOCALES_DIR / f"{locale}.json"
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"locale catalog {path} must be a JSON object")
    entries = cast(dict[object, object], raw)
    catalog: dict[str, str] = {}
    for key, value in entries.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError(f"locale catalog {path}: non-string entry {key!r}")
        catalog[key] = value
    return catalog


def catalog(locale: str | None = None) -> dict[str, str]:
    """Return the full flat catalog for ``locale`` (read-only by convention)."""
    return _load_catalog(_loc(locale))


def _split_label_key(key: str) -> tuple[str, str] | None:
    if not key.startswith(_LABEL_PREFIX):
        return None
    rest = key[len(_LABEL_PREFIX) :]
    group, sep, item = rest.partition(".")
    if not sep or not item:
        return None
    return group, item


@cache
def _label_groups(locale: str) -> dict[str, dict[str, str]]:
    groups: dict[str, dict[str, str]] = {}
    for key, value in _load_catalog(locale).items():
        parsed = _split_label_key(key)
        if parsed is None:
            continue
        group, item = parsed
        groups.setdefault(group, {})[item] = value
    return groups


def _messages(locale: str) -> dict[str, str]:
    return {
        key: value
        for key, value in _load_catalog(locale).items()
        if not key.startswith(_LABEL_PREFIX)
    }


def _by_locale(group: str) -> dict[str, dict[str, str]]:
    return {loc: dict(_label_groups(loc).get(group, {})) for loc in SUPPORTED_LOCALES}


# ---------------------------------------------------------------------------
# Backward-compatible catalog views (derived from JSON at import)
# ---------------------------------------------------------------------------
ARTIFACT_TITLES: dict[str, dict[str, str]] = _by_locale("artifact")
STAGE_LABELS: dict[str, dict[str, str]] = _by_locale("stage")
GATE_LABELS: dict[str, dict[str, str]] = _by_locale("gate")
CARD_LABELS: dict[str, dict[str, str]] = _by_locale("card")
TREND_LABELS: dict[str, dict[str, str]] = _by_locale("trend")
BIAS_LABELS: dict[str, dict[str, str]] = _by_locale("bias")
SETUP_LABELS: dict[str, dict[str, str]] = _by_locale("setup")
DRIVER_LABELS: dict[str, dict[str, str]] = _by_locale("driver")
OUTCOME_STATUS_LABELS: dict[str, dict[str, str]] = _by_locale("outcome_status")
OUTCOME_FIELD_LABELS: dict[str, dict[str, str]] = _by_locale("outcome_field")
DECISION_LABELS: dict[str, tuple[str, str, str]] = {
    decision: (
        _label_groups("en").get("decision_emoji", {}).get(decision, ""),
        _label_groups("ar").get("decision", {}).get(decision, decision),
        label,
    )
    for decision, label in _label_groups("en").get("decision", {}).items()
}
MESSAGES: dict[str, dict[str, str]] = {loc: _messages(loc) for loc in SUPPORTED_LOCALES}

_LABEL_MAP_GROUPS: frozenset[str] = frozenset(
    {
        "card",
        "artifact",
        "stage",
        "gate",
        "trend",
        "bias",
        "setup",
        "driver",
        "outcome_status",
        "outcome_field",
    }
)


def _loc(locale: str | None) -> str:
    return "ar" if normalize_locale(locale) == "ar" else "en"


def tr(key: str, locale: str | None = None, **kwargs: Any) -> str:
    """Look up a message template for the locale and format placeholders."""
    loc = _loc(locale)
    template = _load_catalog(loc).get(key) or _load_catalog("en").get(key) or key
    if kwargs:
        return template.format(**kwargs)
    return template


def label_map(name: str, locale: str | None = None) -> dict[str, str]:
    """Return a label dictionary for card/artifact/stage lookups."""
    if name not in _LABEL_MAP_GROUPS:
        return {}
    loc = _loc(locale)
    labels = _label_groups(loc).get(name)
    if labels is None:
        labels = _label_groups("en").get(name, {})
    return labels


def artifact_title(kind: str, locale: str | None = None) -> str:
    return label_map("artifact", locale).get(kind, kind)


def stage_label(stage: str, locale: str | None = None) -> str:
    return label_map("stage", locale).get(stage, stage)


def gate_label(gate_id: str, locale: str | None = None) -> str:
    """User-facing quality-check name (never show raw G1, G2, … to operators)."""
    key = (gate_id or "").strip()
    catalog = label_map("gate", locale)
    mapped = catalog.get(key) or catalog.get(key.upper(), "")
    if mapped:
        return mapped
    if _RAW_GATE_ID.match(key):
        return ""
    return key
