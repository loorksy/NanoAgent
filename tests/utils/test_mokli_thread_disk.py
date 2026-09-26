"""Tests for Mokli on-disk cleanup (legacy JSON + transcript JSONL)."""

from __future__ import annotations

from mokli.surface.thread_disk import delete_mokli_thread, mokli_thread_file_path
from mokli.surface.transcript import (
    append_transcript_object,
    mokli_transcript_path,
    mokli_transcript_segments_dir,
)


def test_delete_mokli_thread_removes_legacy_json_and_transcript(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.surface.transcript._MAX_TRANSCRIPT_FILE_BYTES", 520)
    monkeypatch.setattr("mokli.surface.transcript._ACTIVE_TRANSCRIPT_ROTATE_BYTES", 520)
    monkeypatch.setattr("mokli.surface.transcript._TARGET_ACTIVE_TRANSCRIPT_BYTES", 260)
    key = "websocket:k1"
    json_path = mokli_thread_file_path(key)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text('{"x":1}', encoding="utf-8")
    for idx in range(1, 5):
        append_transcript_object(
            key,
            {"event": "user", "chat_id": "k1", "text": f"question {idx} " + ("x" * 24)},
        )
        append_transcript_object(
            key,
            {"event": "message", "chat_id": "k1", "text": f"answer {idx} " + ("y" * 24)},
        )
        append_transcript_object(key, {"event": "turn_end", "chat_id": "k1"})
    assert mokli_transcript_path(key).is_file()
    assert mokli_transcript_segments_dir(key).is_dir()
    assert delete_mokli_thread(key) is True
    assert not json_path.is_file()
    assert not mokli_transcript_path(key).is_file()
    assert not mokli_transcript_segments_dir(key).exists()
    assert delete_mokli_thread(key) is False
