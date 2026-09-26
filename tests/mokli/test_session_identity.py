from mokli.mokli.session_identity import (
    MOKLI_SESSION_STORAGE_PREFIX,
    is_valid_mokli_chat_id,
    is_mokli_session_key,
    mokli_chat_id,
    mokli_session_key,
)


def test_mokli_session_identity_preserves_persisted_wire_compatibility() -> None:
    assert MOKLI_SESSION_STORAGE_PREFIX == "websocket:"
    assert mokli_session_key("chat-1") == "websocket:chat-1"
    assert is_mokli_session_key("websocket:chat-1")
    assert mokli_chat_id("websocket:chat-1") == "chat-1"
    assert mokli_chat_id("websocket: chat-1") == " chat-1"
    assert mokli_chat_id("websocket:") is None
    assert mokli_chat_id("telegram:chat-1") is None


def test_mokli_chat_id_validation_is_protocol_scoped() -> None:
    assert is_valid_mokli_chat_id("unified:default")
    assert is_valid_mokli_chat_id("x" * 64)
    assert not is_valid_mokli_chat_id("x" * 65)
    assert not is_valid_mokli_chat_id("../escape")
