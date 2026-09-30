"""Session state phases come from real transitions, not an assumed thinking step."""

from mokli.agent_api.state import StateTracker


def test_approval_resolution_while_the_run_is_open_does_not_claim_thinking() -> None:
    tracker = StateTracker()
    tracker.run_started("s1", "run-1")
    tracker.approval_opened("s1", "a1")
    resolved = tracker.approval_resolved("s1", "a1", outcome="ok")
    assert resolved is not None
    assert resolved["state"] == "working"
    assert resolved["phase"] == "processing"


def test_provider_thinking_is_published_once_per_stretch() -> None:
    tracker = StateTracker()
    tracker.run_started("s1", "run-1")
    first = tracker.working("s1", phase="thinking", provider_thinking=True)
    second = tracker.working("s1", phase="thinking", provider_thinking=True)
    assert first is not None
    assert first["phase"] == "thinking"
    assert first["provider_thinking"] is True
    assert second is None


def test_thinking_ends_when_the_provider_stops() -> None:
    tracker = StateTracker()
    tracker.run_started("s1", "run-1")
    tracker.working("s1", phase="thinking", provider_thinking=True)
    cleared = tracker.working("s1", phase="processing")
    assert cleared is not None
    assert cleared["phase"] == "processing"
    assert "provider_thinking" not in cleared


def test_approval_resolution_after_the_run_finishes_completes() -> None:
    tracker = StateTracker()
    tracker.approval_opened("s1", "a1")
    resolved = tracker.approval_resolved("s1", "a1", outcome="ok")
    assert resolved is not None
    assert resolved["state"] == "completed"
    assert resolved["outcome"] == "ok"
