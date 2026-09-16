"""Operator-facing gate names come from i18n, never raw G1…G20."""

from __future__ import annotations

import re
from typing import get_args

from nanobot.trading.i18n import GATE_LABELS, MESSAGES, gate_label, tr
from nanobot.trading.types import GateId

_RAW_GATE = re.compile(r"\bG\d+\b", re.I)


def test_every_gate_id_has_en_and_ar_names() -> None:
    for gate_id in get_args(GateId):
        en = gate_label(gate_id, "en")
        ar = gate_label(gate_id, "ar")
        assert en and en != gate_id, gate_id
        assert ar and ar != gate_id, gate_id
        assert not _RAW_GATE.search(en), en
        assert not _RAW_GATE.search(ar), ar
        assert GATE_LABELS["en"][gate_id] == en
        assert GATE_LABELS["ar"][gate_id] == ar


def test_gate_label_never_returns_raw_wire_id() -> None:
    assert gate_label("G99", "en") == ""
    assert gate_label("g12", "ar") == GATE_LABELS["ar"]["G12"]
    assert not _RAW_GATE.search(gate_label("G1", "en"))


def test_operator_catalog_values_do_not_mention_gate_ids() -> None:
    for locale, catalog in MESSAGES.items():
        for key, value in catalog.items():
            assert not _RAW_GATE.search(value), f"{locale}:{key}"
    for locale, catalog in GATE_LABELS.items():
        for gate_id, label in catalog.items():
            assert not _RAW_GATE.search(label), f"{locale}:{gate_id}"


def test_risk_parameter_labels_do_not_mention_gate_ids() -> None:
    for key in (
        "risk.field.news_blackout_before_minutes",
        "risk.field.news_blackout_after_minutes",
        "risk.field.max_reprice_rounds",
        "risk.field.g7_max_slippage_atr",
        "gate.blocked",
    ):
        assert not _RAW_GATE.search(tr(key, "en", check="x", reason="y")), key
        assert not _RAW_GATE.search(tr(key, "ar", check="x", reason="y")), key
