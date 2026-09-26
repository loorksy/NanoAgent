from mokli.config.schema import Config, TradingRiskParameters
from mokli.trading.gates.news_policy import news_gate_mode


def _with_mode(monkeypatch, mode: str | None) -> None:
    params = TradingRiskParameters() if mode is None else TradingRiskParameters(news_gate_mode=mode)  # type: ignore[arg-type]
    cfg = Config(trading_risk_parameters=params)
    monkeypatch.setattr("mokli.config.loader.load_config", lambda *_a, **_k: cfg)


def test_news_gate_mode_defaults_to_warn(monkeypatch) -> None:
    _with_mode(monkeypatch, None)
    assert news_gate_mode() == "warn"


def test_news_gate_mode_strict(monkeypatch) -> None:
    _with_mode(monkeypatch, "strict")
    assert news_gate_mode() == "strict"


def test_news_gate_mode_off(monkeypatch) -> None:
    _with_mode(monkeypatch, "off")
    assert news_gate_mode() == "off"


def test_news_gate_mode_falls_back_when_config_unreadable(monkeypatch) -> None:
    def _boom(*_a, **_k):
        raise OSError("no config")

    monkeypatch.setattr("mokli.config.loader.load_config", _boom)
    assert news_gate_mode() == "warn"
