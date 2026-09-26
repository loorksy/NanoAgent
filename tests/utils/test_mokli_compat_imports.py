import importlib

from mokli.session import mokli_turns
from mokli.mokli import thread_disk, transcript


def test_legacy_mokli_utils_imports_resolve_to_new_modules() -> None:
    legacy_thread_disk = importlib.import_module("mokli.utils.mokli_thread_disk")
    legacy_transcript = importlib.import_module("mokli.utils.mokli_transcript")
    legacy_turn_helpers = importlib.import_module("mokli.utils.mokli_turn_helpers")

    assert legacy_thread_disk.delete_mokli_thread is thread_disk.delete_mokli_thread
    assert legacy_transcript.append_transcript_object is transcript.append_transcript_object
    assert legacy_turn_helpers.mark_mokli_session is mokli_turns.mark_mokli_session
