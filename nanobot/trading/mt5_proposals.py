"""In-memory HITL order proposals — propose never sends, confirm requires operator ack."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from nanobot.trading.policy import live


@dataclass
class OrderProposal:
    id: str
    created_ms: int
    expires_ms: int
    symbol: str
    side: str
    lot: float
    entry: float
    stop: float
    targets: list[float]
    comment: str = ""
    order_type: str = "market"
    confirmed: bool = False
    executed: bool = False
    position_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("extra", None)
        return data


class ProposalStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, OrderProposal] = {}

    def create(
        self,
        *,
        symbol: str,
        side: str,
        lot: float,
        entry: float,
        stop: float,
        targets: list[float],
        comment: str = "",
        order_type: str = "market",
        now_ms: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> OrderProposal:
        now = now_ms if now_ms is not None else int(time.time() * 1000)
        item = OrderProposal(
            id=uuid.uuid4().hex,
            created_ms=now,
            expires_ms=now + int(live().PROPOSAL_TTL_SECONDS * 1000),
            symbol=symbol,
            side=side,
            lot=lot,
            entry=entry,
            stop=stop,
            targets=list(targets),
            comment=comment,
            order_type=order_type,
            extra=extra or {},
        )
        with self._lock:
            self._items[item.id] = item
        return item

    def get(self, proposal_id: str) -> OrderProposal | None:
        with self._lock:
            return self._items.get(proposal_id)

    def mark_confirmed(self, proposal_id: str) -> OrderProposal | None:
        with self._lock:
            item = self._items.get(proposal_id)
            if item is None:
                return None
            item.confirmed = True
            return item

    def mark_executed(self, proposal_id: str, position_id: str) -> OrderProposal | None:
        with self._lock:
            item = self._items.get(proposal_id)
            if item is None:
                return None
            item.executed = True
            item.position_id = position_id
            return item


_STORE: ProposalStore | None = None


def get_proposal_store() -> ProposalStore:
    global _STORE
    if _STORE is None:
        _STORE = ProposalStore()
    return _STORE
