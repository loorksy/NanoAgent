"""Company directory behind the official MetaTrader broker search.

The Python MetaTrader5 package has no company search. This module asks the
same public company index the terminal uses, keeps each server's access
address on the server, and returns only company and server names.
"""

from __future__ import annotations

import re
import threading
from typing import Any

_SEARCH_URL = "https://mt5ex.mtapi.io/Search"
_MIN_QUERY = 2
_MAX_QUERY = 64
_MAX_COMPANIES = 30
_MAX_SERVERS = 40
_TIMEOUT = 8.0
_SUFFIXES = ("-Trade", "-Live", "-Demo", "-Real", "-Trial")
_HOST = re.compile(
    r"(?i)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+"
)

_lock = threading.Lock()
_access_by_server: dict[str, str] = {}


class Mt5DirectoryError(Exception):
    """The company index did not answer."""


def clear_directory_cache() -> None:
    with _lock:
        _access_by_server.clear()


def looks_like_address(value: str) -> bool:
    """True for ``host:port`` or ``[ipv6]:port``."""
    text = value.strip()
    if text.startswith("["):
        host, separator, port_text = text.rpartition("]:")
        if separator != "]:" or not host.startswith("["):
            return False
        return _port_ok(port_text) and ":" in host
    host, separator, port_text = text.rpartition(":")
    if separator != ":" or not _port_ok(port_text):
        return False
    parts = host.split(".")
    if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
        return True
    return _HOST.fullmatch(host) is not None


def search_companies(query: str) -> list[dict[str, Any]]:
    """Companies and server names for a broker search. Access addresses stay here."""
    text = _clean_query(query)
    if len(text) < _MIN_QUERY:
        return []
    parsed = _parse(_fetch(text))
    _remember(parsed)
    return _public(parsed)


def resolve_access(server: str, *, company: str = "") -> str:
    """Access ``host:port`` for ``initialize(server=...)``.

    A typed address is returned as itself. A server chosen from the company
    list is resolved from the directory. An empty string means the name is
    not in the index.
    """
    name = server.strip()
    if looks_like_address(name):
        return name
    cached = _cached(name)
    if cached:
        return cached
    candidates: list[str] = []
    for raw in (company, name):
        text = _clean_query(raw)
        if len(text) >= _MIN_QUERY and text not in candidates:
            candidates.append(text)
    failures = 0
    for text in candidates:
        try:
            parsed = _parse(_fetch(text))
        except Mt5DirectoryError:
            failures += 1
            continue
        _remember(parsed)
        cached = _cached(name)
        if cached:
            return cached
    if candidates and failures == len(candidates):
        raise Mt5DirectoryError("directory unavailable")
    return ""


def _clean_query(value: str) -> str:
    return " ".join(value.split())[:_MAX_QUERY]


def _port_ok(value: str) -> bool:
    return value.isdigit() and 1 <= int(value) <= 65535


def _prefer(addresses: list[str]) -> str:
    usable = [item for item in addresses if looks_like_address(item)]
    for item in usable:
        if not item.startswith("["):
            return item
    return usable[0] if usable else ""


def _label(servers: list[str]) -> str:
    stems: list[str] = []
    for name in servers:
        stem = name
        for suffix in _SUFFIXES:
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        stems.append(stem)
    if len(set(stems)) == 1:
        return stems[0]
    return servers[0]


def _parse(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise Mt5DirectoryError("directory payload was not a company list")
    companies: list[dict[str, Any]] = []
    for item in payload:
        if len(companies) >= _MAX_COMPANIES or not isinstance(item, dict):
            continue
        name = str(item.get("companyName") or "").strip()
        if not name:
            continue
        servers: list[str] = []
        access: dict[str, str] = {}
        for row in item.get("results") or []:
            if len(servers) >= _MAX_SERVERS or not isinstance(row, dict):
                continue
            server_name = str(row.get("name") or "").strip()
            if not server_name or server_name in access:
                continue
            chosen = _prefer([str(entry).strip() for entry in (row.get("access") or [])])
            if not chosen:
                continue
            servers.append(server_name)
            access[server_name] = chosen
        if not servers:
            continue
        companies.append(
            {"name": name, "label": _label(servers), "servers": servers, "access": access}
        )
    return companies


def _public(companies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"name": company["name"], "label": company["label"], "servers": list(company["servers"])}
        for company in companies
    ]


def _remember(companies: list[dict[str, Any]]) -> None:
    with _lock:
        for company in companies:
            access = company.get("access")
            if isinstance(access, dict):
                for server_name, address in access.items():
                    if isinstance(server_name, str) and isinstance(address, str) and address:
                        _access_by_server[server_name] = address


def _cached(server_name: str) -> str:
    with _lock:
        return _access_by_server.get(server_name, "")


def _fetch(query: str) -> object:
    import httpx

    try:
        response = httpx.get(_SEARCH_URL, params={"company": query}, timeout=_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise Mt5DirectoryError("directory unavailable") from exc
