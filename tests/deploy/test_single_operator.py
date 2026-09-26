"""One operator: no second account, no second chat door, no fake model controls."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_second_account_is_refused_at_the_auth_insert() -> None:
    source = _text("open-webui/backend/open_webui/models/auths.py")
    assert "if await Users.has_users(db=session):" in source
    assert "one operator only" in source


def test_signup_and_add_user_do_not_open_a_second_account() -> None:
    source = _text("open-webui/backend/open_webui/routers/auths.py")
    signup = source.split("async def signup(", 1)[1].split("async def", 1)[0]
    assert "if has_users:" in signup
    assert "enable_signup" not in signup
    added = source.split("async def add_user(", 1)[1].split("async def", 1)[0]
    assert "insert_new_auth" not in added
    assert "ACCESS_PROHIBITED" in added


def test_chat_model_list_is_the_pipe_only() -> None:
    source = _text("open-webui/backend/open_webui/main.py")
    assert "isinstance(model.get('pipe'), dict)" in source


def test_signup_link_and_add_user_button_are_gone() -> None:
    auth = _text("open-webui/src/routes/auth/+page.svelte")
    assert "Don't have an account?" not in auth
    users = _text("open-webui/src/lib/components/admin/Users/UserList.svelte")
    assert "Add User" not in users
    assert "AddUserModal" not in users


def test_system_prompt_and_temperature_controls_are_gone() -> None:
    general = _text("open-webui/src/lib/components/chat/Settings/General.svelte")
    controls = _text("open-webui/src/lib/components/chat/Controls/Controls.svelte")
    assert "sections.systemPrompt" not in general
    assert "temperature:" not in general
    assert "System Prompt" not in controls
    assert "Advanced Params" not in controls
    chat = _text("open-webui/src/lib/components/chat/Chat.svelte")
    assert "role: 'system'" not in chat
    assert "selectedModelIds = [atSelectedModel.id]" not in chat
    message_input = _text("open-webui/src/lib/components/chat/MessageInput.svelte")
    assert "atSelectedModel = data" not in message_input
    assert "atSelectedModel = model" not in message_input
