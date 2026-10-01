"""Fold live subagent events into desk cards and stop a swarm between layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from mokli.agent_api.events import subagent_data
from mokli.trading.teams.subagent_runner import TeamAgentEvent

CardStage = Literal["started", "finished"]


@dataclass
class SwarmCard:
    role_id: str
    role: str
    room_id: str
    layer: int
    stage: str
    summary: str = ""


@dataclass
class SwarmBoard:
    cards: list[SwarmCard] = field(default_factory=list)

    def note(self, event: dict[str, object]) -> None:
        role_id = str(event.get("role_id") or event.get("id") or "")
        if not role_id:
            return
        layer_raw = event.get("layer")
        layer = layer_raw if isinstance(layer_raw, int) else 0
        card = SwarmCard(
            role_id=role_id,
            role=str(event.get("role") or role_id),
            room_id=str(event.get("room_id") or ""),
            layer=layer,
            stage=str(event.get("event") or "started"),
            summary=str(event.get("summary") or ""),
        )
        self.cards = [item for item in self.cards if item.role_id != role_id]
        self.cards.append(card)


def reduce_board(events: list[dict[str, object]]) -> list[SwarmCard]:
    board = SwarmBoard()
    for event in events:
        board.note(event)
    return list(board.cards)


class SwarmControl:
    """Checked between swarm layers. Cancelling does not touch MT5."""

    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


_active: SwarmControl | None = None


def bind_swarm_control(control: SwarmControl | None) -> None:
    global _active
    _active = control


def request_swarm_stop() -> bool:
    if _active is None:
        return False
    _active.cancel()
    return True


def team_subagent_event(event: TeamAgentEvent, stage: CardStage) -> dict[str, object]:
    summary = event.summary or None
    if stage == "started":
        summary = None
    return subagent_data(
        stage,
        id=event.agent_id,
        role=event.role,
        summary=summary,
        room_id=event.room_id or None,
        role_id=event.role_id or event.agent_id,
        layer=event.layer,
    )
