"""CFTC gold positioning snapshot (R9).

Parsing is local. ``load_gold_cot`` calls the public Socrata dataset unless a
test injects ``http_get``. Failures return an empty snapshot.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from typing import cast

CFTC_GOLD_URL = (
    "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
    "?commodity_name=GOLD&$limit=8&$order=report_date_as_yyyy_mm_dd DESC"
)

_COMM_LONG = (
    "comm_positions_long_all",
    "prod_merc_positions_long",
    "commercial_long",
)
_COMM_SHORT = (
    "comm_positions_short_all",
    "prod_merc_positions_short",
    "commercial_short",
)
_SPEC_LONG = (
    "m_money_positions_long_all",
    "noncomm_positions_long_all",
    "spec_long",
)
_SPEC_SHORT = (
    "m_money_positions_short_all",
    "noncomm_positions_short_all",
    "spec_short",
)


def cot_bias(spec_net: int) -> str:
    if spec_net > 0:
        return "bullish"
    if spec_net < 0:
        return "bearish"
    return "neutral"


def _int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def snapshot_from_rows(rows: list[dict[str, object]], *, market: str = "gold") -> dict[str, object]:
    if not rows:
        return {
            "market": market,
            "commercial_net": 0,
            "spec_net": 0,
            "bias": "neutral",
            "notice_key": "cot.bias_neutral",
            "available": False,
        }
    last = rows[-1]
    spec_net = _int(last.get("spec_net"))
    bias = cot_bias(spec_net)
    notice = {
        "bullish": "cot.bias_bullish",
        "bearish": "cot.bias_bearish",
        "neutral": "cot.bias_neutral",
    }[bias]
    return {
        "market": market,
        "commercial_net": _int(last.get("commercial_net")),
        "spec_net": spec_net,
        "bias": bias,
        "notice_key": notice,
        "available": True,
    }


def _first(row: dict[str, object], keys: tuple[str, ...]) -> int:
    for key in keys:
        if key in row:
            return _int(row.get(key))
    return 0


def rows_from_cftc(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Map Socrata long/short columns onto commercial and speculative nets."""
    mapped: list[dict[str, object]] = []
    for row in rows:
        report_date = str(row.get("report_date_as_yyyy_mm_dd") or "")
        if "commercial_net" in row or "spec_net" in row:
            mapped.append(
                {
                    "commercial_net": _int(row.get("commercial_net")),
                    "spec_net": _int(row.get("spec_net")),
                    "report_date": report_date,
                }
            )
            continue
        mapped.append(
            {
                "commercial_net": _first(row, _COMM_LONG) - _first(row, _COMM_SHORT),
                "spec_net": _first(row, _SPEC_LONG) - _first(row, _SPEC_SHORT),
                "report_date": report_date,
            }
        )
    mapped.sort(key=lambda item: str(item.get("report_date") or ""))
    return mapped


def _default_http_get(url: str) -> list[dict[str, object]]:
    with urllib.request.urlopen(url, timeout=8) as response:
        raw: object = json.loads(response.read().decode("utf-8"))
    rows: list[dict[str, object]] = []
    if not isinstance(raw, list):
        return rows
    for item in cast(list[object], raw):
        if isinstance(item, dict):
            rows.append(cast(dict[str, object], item))
    return rows


def fetch_cot(
    http_get: Callable[[str], list[dict[str, object]]],
    url: str,
) -> dict[str, object]:
    return snapshot_from_rows(rows_from_cftc(http_get(url)))


def load_gold_cot(
    http_get: Callable[[str], list[dict[str, object]]] | None = None,
) -> dict[str, object]:
    """Load the latest public gold COT report. Network errors are an empty snapshot."""
    getter = http_get or _default_http_get
    try:
        payload = getter(CFTC_GOLD_URL)
    except Exception:
        return snapshot_from_rows([])
    return snapshot_from_rows(rows_from_cftc(payload))
