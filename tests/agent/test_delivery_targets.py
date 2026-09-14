"""Cross-channel delivery target resolution."""

from nanobot.agent.delivery_targets import (
    default_telegram_chat_id,
    resolve_telegram_chat_id,
    telegram_chat_id_from_sender,
)


def test_telegram_chat_id_from_sender() -> None:
    assert telegram_chat_id_from_sender("5969744996|aswadtr") == "5969744996"
    assert telegram_chat_id_from_sender("5969744996") == "5969744996"
    assert telegram_chat_id_from_sender("b7508e2c-ac4a-4a9d-a51a-970409fb146c") is None


def test_resolve_telegram_chat_id_rejects_uuid() -> None:
    assert resolve_telegram_chat_id("5969744996") == "5969744996"
    assert resolve_telegram_chat_id("b7508e2c-ac4a-4a9d-a51a-970409fb146c") is None


def test_default_telegram_chat_id_from_pairing(monkeypatch) -> None:
    monkeypatch.setattr(
        "nanobot.agent.delivery_targets.get_approved",
        lambda _channel: ["5969744996|aswadtr"],
    )
    assert default_telegram_chat_id() == "5969744996"
