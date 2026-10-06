"""Locale catalogs (``mokli/trading/locales/*.json``) stay in sync and Arabic stays out of code."""

from __future__ import annotations

import json
import re
from pathlib import Path
from string import Formatter

import pytest

from mokli.trading import i18n
from mokli.trading.i18n import (
    CARD_LABELS,
    DECISION_LABELS,
    GATE_LABELS,
    MESSAGES,
    SUPPORTED_LOCALES,
    catalog,
    label_map,
    tr,
)

LOCALES_DIR = Path("mokli/trading/locales")
TRADING_DIR = Path("mokli/trading")
_ARABIC = re.compile(r"[\u0600-\u06FF]")
_RAW_GATE = re.compile(r"\bG\d+\b", re.I)

# Owned by the keyword-router removal package (D3); it disappears with that work.
_ARABIC_ALLOWLIST = {
    TRADING_DIR / "operator_keywords.py",
    # User-facing phrases for team activity; not model prompt text.
    TRADING_DIR / "teams" / "role_display.py",
    # Arabic buy/sell and strategy description patterns matched in user text.
    TRADING_DIR / "decision_route.py",
    TRADING_DIR / "strategy_spec.py",
}


def _raw(locale: str) -> dict[str, str]:
    data = json.loads((LOCALES_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in Formatter().parse(template) if name}


def test_supported_locales_have_catalog_files() -> None:
    assert set(SUPPORTED_LOCALES) == {"en", "ar"}
    for locale in SUPPORTED_LOCALES:
        assert (LOCALES_DIR / f"{locale}.json").is_file()


def test_catalogs_are_flat_string_maps() -> None:
    for locale in SUPPORTED_LOCALES:
        for key, value in _raw(locale).items():
            assert isinstance(key, str) and key.strip() == key and key, (locale, key)
            assert isinstance(value, str) and value.strip(), (locale, key)


def test_ar_and_en_have_identical_key_sets() -> None:
    en_keys = set(_raw("en"))
    ar_keys = set(_raw("ar"))
    assert en_keys == ar_keys, {
        "missing_in_ar": sorted(en_keys - ar_keys),
        "missing_in_en": sorted(ar_keys - en_keys),
    }


def test_placeholders_match_between_languages() -> None:
    en = _raw("en")
    ar = _raw("ar")
    for key, template in en.items():
        assert _placeholders(template) == _placeholders(ar[key]), key


def test_arabic_catalog_is_arabic_and_english_catalog_is_not() -> None:
    en = _raw("en")
    ar = _raw("ar")
    for key, value in en.items():
        assert not _ARABIC.search(value), f"en:{key}"
    arabic_keys = [key for key, value in ar.items() if _ARABIC.search(value)]
    # Emoji, symbols, and shared tokens (XAUUSD, UTC) may be identical; the bulk must be Arabic.
    assert len(arabic_keys) > len(ar) * 0.9


def test_catalog_values_never_mention_raw_gate_ids() -> None:
    for locale in SUPPORTED_LOCALES:
        for key, value in _raw(locale).items():
            if key.startswith("label.gate."):
                continue
            assert not _RAW_GATE.search(value), f"{locale}:{key}"


def test_tr_missing_key_returns_key_unchanged() -> None:
    assert tr("does.not.exist") == "does.not.exist"
    assert tr("does.not.exist", "ar") == "does.not.exist"
    assert tr("does.not.exist", "ar", value=1) == "does.not.exist"


def test_tr_unknown_locale_falls_back_to_english() -> None:
    assert tr("price.header", "fr") == tr("price.header", "en")
    assert tr("price.header", None) == tr("price.header", "en")
    assert tr("price.header", "AR-sa") == tr("price.header", "ar")


def test_tr_formats_placeholders() -> None:
    assert tr("price.fetch_failed", "en", error="boom").endswith("boom")
    assert "boom" in tr("price.fetch_failed", "ar", error="boom")


def test_label_maps_are_derived_from_flat_catalog() -> None:
    assert label_map("card", "ar")["entry"] == catalog("ar")["label.card.entry"]
    assert label_map("gate", "en")["G1"] == catalog("en")["label.gate.G1"]
    assert label_map("unknown_group", "en") == {}
    assert CARD_LABELS["en"]["entry"] == "Entry"
    assert GATE_LABELS["ar"]["G1"] == catalog("ar")["label.gate.G1"]


def test_decision_labels_keep_tuple_shape() -> None:
    assert set(DECISION_LABELS) == {"buy", "sell", "wait"}
    emoji, arabic, english = DECISION_LABELS["buy"]
    assert emoji and _ARABIC.search(arabic) and english == "BUY"


def test_messages_exclude_label_groups() -> None:
    for locale in SUPPORTED_LOCALES:
        assert not any(key.startswith("label.") for key in MESSAGES[locale])
        assert "price.header" in MESSAGES[locale]


def test_catalog_loading_is_cached() -> None:
    assert i18n.catalog("en") is i18n.catalog("en")


@pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
def test_every_message_key_is_reachable_via_tr(locale: str) -> None:
    for key, template in _raw(locale).items():
        if _placeholders(template):
            continue
        assert tr(key, locale) == template


def test_no_arabic_script_in_trading_python_sources() -> None:
    offenders: list[str] = []
    for path in sorted(TRADING_DIR.rglob("*.py")):
        if path in _ARABIC_ALLOWLIST:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _ARABIC.search(line):
                offenders.append(f"{path}:{lineno}")
    assert offenders == []


def test_no_arabic_script_in_trading_mokli_api() -> None:
    text = Path("mokli/surface/trading_api.py").read_text(encoding="utf-8")
    assert not _ARABIC.search(text)
