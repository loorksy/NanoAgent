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


def test_approval_resolution_after_the_run_finishes_completes() -> None:
    tracker = StateTracker()
    tracker.approval_opened("s1", "a1")
    resolved = tracker.approval_resolved("s1", "a1", outcome="ok")
    assert resolved is not None
    assert resolved["state"] == "completed"
    assert resolved["outcome"] == "ok"
