import json
import time
import uuid

import pytest

from nanobot.trading.recommendations import store
from nanobot.trading.recommendations.supersede import (
    apply_supersede_transition,
    clear_supersede_pending,
    mark_supersede_pending,
)


def _seed_live(session_key: str, rec_id: str) -> None:
    with store._conn() as conn:
        conn.execute(
            """
            INSERT INTO recommendations
            (id, symbol, interval, direction, entry, stop_loss, targets_json, status,
             summary, confidence, drawings_json, gate_json, created_at, session_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec_id,
                "XAUUSD",
                "15m",
                "buy",
                2650.0,
                2640.0,
                json.dumps([2660.0]),
                "valid_now",
                "test",
                0.7,
                "[]",
                None,
                int(time.time() * 1000),
                session_key,
            ),
        )
        conn.commit()


@pytest.fixture()
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr("nanobot.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("nanobot.trading.recommendations.store.get_data_dir", lambda: tmp_path)
    store._conn().close()
    yield


def test_supersede_reject_keeps_live(isolated_store) -> None:
    session_key = f"websocket:chat-supersede-reject-{uuid.uuid4().hex[:8]}"
    rec_id = f"rec-{uuid.uuid4().hex}"
    _seed_live(session_key, rec_id)
    live = store.latest_live_recommendation(session_key)
    assert live is not None
    mark_supersede_pending(session_key, live)
    result = apply_supersede_transition(
        session_key,
        recommendation_id=str(live["id"]),
        action="reject_new",
    )
    assert result["ok"] is True
    kept = store.latest_live_recommendation(session_key)
    assert kept is not None
    assert kept["status"] == "valid_now"
    clear_supersede_pending(session_key)


def test_supersede_approve_closes_live(isolated_store) -> None:
    session_key = f"websocket:chat-supersede-approve-{uuid.uuid4().hex[:8]}"
    rec_id = f"rec-{uuid.uuid4().hex}"
    _seed_live(session_key, rec_id)
    live = store.latest_live_recommendation(session_key)
    assert live is not None
    mark_supersede_pending(session_key, live)
    result = apply_supersede_transition(
        session_key,
        recommendation_id=str(live["id"]),
        action="approve_new",
    )
    assert result["ok"] is True
    closed = store.get_recommendation(rec_id)
    assert closed is not None
    assert closed["status"] == "superseded"
    assert store.latest_live_recommendation(session_key) is None
    clear_supersede_pending(session_key)
