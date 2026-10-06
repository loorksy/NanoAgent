"""Linked-chat titles must use the same session metadata as the sidebar."""

import json
from pathlib import Path
from typing import Any

import pytest

from mokli.cron.types import CronJob, CronPayload
from mokli.session.manager import SessionManager
from mokli.surface.session_automations import serialize_automation_jobs
from mokli.triggers.local_types import LocalTrigger


@pytest.mark.parametrize(
    ("metadata", "title"),
    [
        ({"title": "推特大战场"}, "推特大战场"),
        ({"title": "<think>internal</think>Release planning"}, "Release planning"),
        ({"title": "<think>literal</think>", "title_user_edited": True}, "<think>literal</think>"),
        ({"title": 42}, ""),
        ({}, ""),
    ],
)
def test_linked_chat_title_reads_current_session_metadata(
    tmp_path: Path, metadata: dict[str, Any], title: str,
) -> None:
    manager = SessionManager(tmp_path)
    key = "websocket:linked-chat"
    session = manager.get_or_create(key)
    session.metadata.update(metadata)
    session.add_message("user", "Original message preview")
    manager.save(session)
    cron = CronJob(
        id="reminder", name="Drink water",
        payload=CronPayload(
            message="Take a break", session_key=key,
            origin_channel="websocket", origin_chat_id="linked-chat",
        ),
    )
    trigger = LocalTrigger(
        id="trigger", name="Build finished", enabled=True,
        channel="websocket", chat_id="linked-chat", session_key=key,
    )

    for expected in (title, "Updated title"):
        rows = serialize_automation_jobs([cron, trigger], include_details=True, session_manager=manager)
        for row in rows:
            assert row["origin"] == {
                "session_key": key,
                "channel": "websocket",
                "chat_id": "linked-chat",
                "title": expected,
                "preview": "Original message preview",
            }
        manager.update_session_metadata(key, {"title": "Updated title"})

    assert cron.payload.session_key == key
    assert cron.payload.message == "Take a break"
    assert trigger.session_key == key


def test_linked_chat_preview_stops_at_the_first_user_line(tmp_path: Path, monkeypatch) -> None:
    """A later transcript line is not parsed for the automation origin preview."""
    manager = SessionManager(tmp_path)
    key = "websocket:linked-chat"
    session = manager.get_or_create(key)
    session.metadata["title"] = "Desk"
    session.add_message("user", "Original message preview")
    session.add_message("assistant", "x" * 80_000)
    manager.save(session)
    cron = CronJob(
        id="reminder",
        name="Drink water",
        payload=CronPayload(
            message="Take a break",
            session_key=key,
            origin_channel="websocket",
            origin_chat_id="linked-chat",
        ),
    )
    loads: list[int] = []
    real_loads = json.loads

    def counting(text: str, *args: object, **kwargs: object) -> object:
        loads.append(len(text))
        return real_loads(text, *args, **kwargs)

    monkeypatch.setattr("mokli.session.manager.json.loads", counting)
    rows = serialize_automation_jobs([cron], include_details=True, session_manager=manager)
    assert rows[0]["origin"]["preview"] == "Original message preview"
    assert rows[0]["origin"]["title"] == "Desk"
    assert len(loads) == 3
    assert max(loads) < 80_000
