"""Company search keeps broker access addresses off the public payload."""

from __future__ import annotations

import json

import pytest

from mokli.trading.mt5_directory import (
    Mt5DirectoryError,
    clear_directory_cache,
    looks_like_address,
    resolve_access,
    search_companies,
)

_SAMPLE = [
    {
        "companyName": "Northwind Markets Limited",
        "results": [
            {
                "name": "Northwind-Trade",
                "access": ["203.0.113.10:443", "203.0.113.11:443", "[2001:db8::10]:443"],
            }
        ],
    },
    {
        "companyName": "Harbor Capital Limited",
        "results": [
            {"name": "HarborCapital-Live", "access": ["203.0.113.20:2002"]},
        ],
    },
]


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_directory_cache()


def test_search_returns_companies_without_access(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mokli.trading.mt5_directory._fetch", lambda query: _SAMPLE)
    rows = search_companies("north")
    blob = json.dumps(rows)
    assert "203.0.113" not in blob
    assert "mtapi" not in blob
    assert "access" not in blob
    assert rows[0] == {
        "name": "Northwind Markets Limited",
        "label": "Northwind",
        "servers": ["Northwind-Trade"],
    }
    assert rows[1]["label"] == "HarborCapital"
    assert rows[1]["servers"] == ["HarborCapital-Live"]


def test_resolve_uses_cached_access_then_company_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fetch(query: str) -> object:
        calls.append(query)
        return _SAMPLE

    monkeypatch.setattr("mokli.trading.mt5_directory._fetch", fetch)
    assert search_companies("north")
    assert calls == ["north"]
    assert resolve_access("Northwind-Trade") == "203.0.113.10:443"
    clear_directory_cache()
    assert resolve_access("Northwind-Trade", company="Northwind Markets Limited") == "203.0.113.10:443"
    assert calls == ["north", "Northwind Markets Limited"]


def test_resolve_address_does_not_call_the_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    def fetch(_query: str) -> object:
        raise AssertionError("address lookup must stay local")

    monkeypatch.setattr("mokli.trading.mt5_directory._fetch", fetch)
    assert resolve_access("203.0.113.10:443") == "203.0.113.10:443"
    assert looks_like_address("company.example:443") is True
    assert looks_like_address("Northwind-Trade") is False


def test_unknown_server_is_empty_and_outage_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mokli.trading.mt5_directory._fetch", lambda _query: _SAMPLE)
    assert resolve_access("Missing-Trade", company="Northwind Markets Limited") == ""
    clear_directory_cache()

    def down(_query: str) -> object:
        raise Mt5DirectoryError("down")

    monkeypatch.setattr("mokli.trading.mt5_directory._fetch", down)
    with pytest.raises(Mt5DirectoryError):
        resolve_access("Northwind-Trade", company="Northwind Markets Limited")


def test_short_query_skips_the_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fetch(_query: str) -> object:
        raise AssertionError("short query must not search")

    monkeypatch.setattr("mokli.trading.mt5_directory._fetch", fetch)
    assert search_companies(" f ") == []


def test_ipv6_only_access_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {
            "companyName": "Example Ltd",
            "results": [{"name": "Example-Live", "access": ["[2001:db8::20]:443"]}],
        }
    ]
    monkeypatch.setattr("mokli.trading.mt5_directory._fetch", lambda _query: payload)
    assert search_companies("example")[0]["servers"] == ["Example-Live"]
    assert resolve_access("Example-Live") == "[2001:db8::20]:443"
