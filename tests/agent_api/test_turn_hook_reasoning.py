"""Thinking status is published only from a real provider reasoning delta."""

from mokli.agent_api.sessions import TurnHook
from mokli.agent_api.state import StateTracker


class _Hub:
    def __init__(self) -> None:
        self.state = StateTracker()
        self.published: list[dict[str, object]] = []

    def working(
        self,
        session: str,
        phase: str,
        *,
        run: str | None = None,
        provider_thinking: bool = False,
    ) -> None:
        data = self.state.working(
            session, phase=phase, provider_thinking=provider_thinking,
        )
        if data is not None:
            self.published.append(dict(data))


async def test_a_reasoning_delta_publishes_thinking_once() -> None:
    hub = _Hub()
    hook = TurnHook(hub, object(), session="s1", run="r1")  # type: ignore[arg-type]
    await hook.emit_reasoning("the level holds")
    await hook.emit_reasoning(" if the hour closes above it")
    assert len(hub.published) == 1
    assert hub.published[0]["phase"] == "thinking"
    assert hub.published[0]["provider_thinking"] is True


async def test_an_empty_reasoning_delta_publishes_nothing() -> None:
    hub = _Hub()
    hook = TurnHook(hub, object(), session="s1", run="r1")  # type: ignore[arg-type]
    await hook.emit_reasoning("")
    await hook.emit_reasoning(None)
    assert hub.published == []


async def test_reasoning_end_returns_to_processing() -> None:
    hub = _Hub()
    hook = TurnHook(hub, object(), session="s1", run="r1")  # type: ignore[arg-type]
    await hook.emit_reasoning_end()
    assert hub.published == []
    await hook.emit_reasoning("checking the close")
    await hook.emit_reasoning_end()
    assert hub.published[-1]["phase"] == "processing"
    assert "provider_thinking" not in hub.published[-1]
