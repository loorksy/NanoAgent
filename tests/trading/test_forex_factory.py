from mokli.trading.news.forex_factory import fetch_upcoming_events
from mokli.trading.turn_session import turn_session_scope


class _Body:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_Body":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def test_forex_factory_disabled_by_default() -> None:
    assert fetch_upcoming_events() == []


def test_turn_downloads_the_calendar_once(monkeypatch) -> None:
    monkeypatch.setenv("FOREX_FACTORY_ENABLED", "1")
    calls = {"n": 0}
    payload = b'[{"country":"USD","impact":"High","title":"CPI","date":"t"}]'

    def urlopen(*_args, **_kwargs):
        calls["n"] += 1
        return _Body(payload)

    monkeypatch.setattr("mokli.trading.news.forex_factory.urllib.request.urlopen", urlopen)
    with turn_session_scope() as turn:
        first = fetch_upcoming_events()
        second = fetch_upcoming_events()
        other_limit = fetch_upcoming_events(limit=3)
    assert calls["n"] == 2
    assert turn.calendar_reuses == 1
    assert first == second == [{"title": "CPI", "currency": "USD", "impact": "high", "time": "t"}]
    assert other_limit == first
    fetch_upcoming_events()
    assert calls["n"] == 3


def test_failed_calendar_download_is_not_cached(monkeypatch) -> None:
    monkeypatch.setenv("FOREX_FACTORY_ENABLED", "1")
    calls = {"n": 0}
    payload = b'[{"country":"USD","impact":"High","title":"CPI","date":"t"}]'

    def urlopen(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("down")
        return _Body(payload)

    monkeypatch.setattr("mokli.trading.news.forex_factory.urllib.request.urlopen", urlopen)
    with turn_session_scope() as turn:
        first = fetch_upcoming_events()
        second = fetch_upcoming_events()
    assert first == []
    assert second[0]["title"] == "CPI"
    assert calls["n"] == 2
    assert turn.calendar_reuses == 0


def test_overlapping_calendar_reads_download_once(monkeypatch) -> None:
    import contextvars
    import threading
    import time

    from mokli.trading.turn_session import turn_session_scope

    monkeypatch.setenv("FOREX_FACTORY_ENABLED", "1")
    entered = {"n": 0}
    release = threading.Event()
    payload = b'[{"country":"USD","impact":"High","title":"CPI","date":"t"}]'

    def urlopen(*_args, **_kwargs):
        entered["n"] += 1
        assert release.wait(timeout=1)
        return _Body(payload)

    monkeypatch.setattr("mokli.trading.news.forex_factory.urllib.request.urlopen", urlopen)
    errors: list[BaseException] = []
    with turn_session_scope() as turn:
        contexts = [contextvars.copy_context() for _ in range(2)]

        def _run(ctx: contextvars.Context) -> None:
            try:
                ctx.run(fetch_upcoming_events)
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_run, args=(ctx,)) for ctx in contexts]
        for thread in threads:
            thread.start()
        deadline = time.time() + 1
        while entered["n"] < 1 and time.time() < deadline:
            time.sleep(0.01)
        time.sleep(0.05)
        assert entered["n"] == 1
        release.set()
        for thread in threads:
            thread.join(timeout=1)
            assert not thread.is_alive()
    assert errors == []
    assert entered["n"] == 1
    assert turn.calendar_reuses == 1
