from types import SimpleNamespace

from mokli.cli.mokli_support import _prepare_mokli_bundle_for_gateway
from mokli.config.schema import Config


def test_source_checkout_preserves_warn_only_gateway_startup(monkeypatch) -> None:
    modes: list[str] = []
    monkeypatch.setattr(
        "mokli.cli.mokli_support.inspect_mokli_bundle",
        lambda: SimpleNamespace(source_available=True),
    )
    monkeypatch.setattr("mokli.cli.mokli_support._mokli_channel_enabled", lambda _config: True)
    monkeypatch.setattr(
        "mokli.cli.mokli_support.ensure_mokli_bundle",
        lambda **kwargs: modes.append(kwargs["mode"]),
    )

    _prepare_mokli_bundle_for_gateway(Config(), mode="warn")

    assert modes == ["warn"]


def test_skip_mode_does_not_build_the_source_mokli_bundle(monkeypatch) -> None:
    modes: list[str] = []
    monkeypatch.setattr(
        "mokli.cli.mokli_support.inspect_mokli_bundle",
        lambda: SimpleNamespace(source_available=True),
    )
    monkeypatch.setattr("mokli.cli.mokli_support._mokli_channel_enabled", lambda _config: True)
    monkeypatch.setattr(
        "mokli.cli.mokli_support.ensure_mokli_bundle",
        lambda **kwargs: modes.append(kwargs["mode"]),
    )

    _prepare_mokli_bundle_for_gateway(Config(), mode="skip")

    assert modes == ["skip"]
