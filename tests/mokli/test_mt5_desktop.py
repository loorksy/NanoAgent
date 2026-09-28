from __future__ import annotations

import base64

from mokli.surface.mt5_desktop import desktop_authorization, upstream_http_url, upstream_ws_url


def test_desktop_urls_follow_the_terminal_window(monkeypatch) -> None:
    monkeypatch.setenv("MT5_DESKTOP_URL", "http://127.0.0.1:32768/")
    assert upstream_http_url("vnc/index.html", "autoconnect=1") == (
        "http://127.0.0.1:32768/vnc/index.html?autoconnect=1"
    )
    assert upstream_http_url("", "") == "http://127.0.0.1:32768/"
    assert upstream_ws_url() == "ws://127.0.0.1:32768/websockify"
    monkeypatch.setenv("MT5_DESKTOP_URL", "https://desktop.internal")
    assert upstream_ws_url() == "wss://desktop.internal/websockify"


def test_desktop_authorization_stays_unset_until_configured(monkeypatch) -> None:
    monkeypatch.delenv("MT5_DESKTOP_USER", raising=False)
    monkeypatch.delenv("MT5_DESKTOP_PASSWORD", raising=False)
    assert desktop_authorization() is None
    monkeypatch.setenv("MT5_DESKTOP_USER", "viewer")
    monkeypatch.setenv("MT5_DESKTOP_PASSWORD", "desktop-secret")
    header = desktop_authorization()
    assert header is not None
    decoded = base64.b64decode(header.removeprefix("Basic ")).decode()
    assert decoded == "viewer:desktop-secret"
