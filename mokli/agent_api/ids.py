"""ULID-style identifiers that sort lexicographically in creation order."""

from __future__ import annotations

import secrets
import threading
import time

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_TIME_CHARS = 10
_RANDOM_CHARS = 16
_RANDOM_BITS = _RANDOM_CHARS * 5
_RANDOM_MAX = (1 << _RANDOM_BITS) - 1


def _encode(value: int, width: int) -> str:
    out: list[str] = []
    for _ in range(width):
        out.append(_ALPHABET[value & 31])
        value >>= 5
    return "".join(reversed(out))


class MonotonicIdGenerator:
    """Generate 26-char ULIDs; ids minted within one millisecond stay strictly increasing."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_ms = -1
        self._last_random = 0

    def next(self, *, now_ms: int | None = None) -> str:
        ts = int(time.time() * 1000) if now_ms is None else int(now_ms)
        with self._lock:
            if ts <= self._last_ms:
                ts = self._last_ms
                self._last_random = (self._last_random + 1) & _RANDOM_MAX
                if self._last_random == 0:
                    ts += 1
                    self._last_random = secrets.randbits(_RANDOM_BITS - 1)
            else:
                self._last_random = secrets.randbits(_RANDOM_BITS - 1)
            self._last_ms = ts
            return _encode(ts, _TIME_CHARS) + _encode(self._last_random, _RANDOM_CHARS)


_DEFAULT = MonotonicIdGenerator()


def new_id(prefix: str = "") -> str:
    """Return a fresh monotonic id, optionally prefixed (``s_``, ``r_``…)."""
    return f"{prefix}{_DEFAULT.next()}"
