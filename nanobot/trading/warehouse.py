"""SQLite OHLC warehouse for gold candles (R3). Feeds D1 history and fast backtests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from nanobot.trading.types import Candle


class CandleWarehouse:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bars (
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                time_ms INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL,
                PRIMARY KEY (symbol, interval, time_ms)
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def upsert(self, symbol: str, interval: str, candles: list[Candle]) -> int:
        rows = [
            (
                symbol,
                interval,
                candle.time_ms,
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.volume,
            )
            for candle in candles
        ]
        self._conn.executemany(
            """
            INSERT INTO bars (symbol, interval, time_ms, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, interval, time_ms) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low,
                close=excluded.close, volume=excluded.volume
            """,
            rows,
        )
        self._conn.commit()
        return len(rows)

    def load(self, symbol: str, interval: str, *, limit: int = 200) -> list[Candle]:
        cur = self._conn.execute(
            """
            SELECT time_ms, open, high, low, close, volume FROM bars
            WHERE symbol = ? AND interval = ?
            ORDER BY time_ms DESC LIMIT ?
            """,
            (symbol, interval, limit),
        )
        rows = list(reversed(cur.fetchall()))
        return [
            Candle(
                time_ms=int(time_ms),
                open=float(open_),
                high=float(high),
                low=float(low),
                close=float(close),
                volume=None if volume is None else float(volume),
            )
            for time_ms, open_, high, low, close, volume in rows
        ]

    def gap_count(self, symbol: str, interval: str, bar_ms: int) -> int:
        times = [
            int(row[0])
            for row in self._conn.execute(
                "SELECT time_ms FROM bars WHERE symbol = ? AND interval = ? ORDER BY time_ms",
                (symbol, interval),
            )
        ]
        gaps = 0
        for older, newer in zip(times, times[1:], strict=False):
            if newer - older > bar_ms:
                gaps += 1
        return gaps

    def last_sync_ms(self, symbol: str, interval: str) -> int | None:
        row = self._conn.execute(
            "SELECT MAX(time_ms) FROM bars WHERE symbol = ? AND interval = ?",
            (symbol, interval),
        ).fetchone()
        if row is None or row[0] is None:
            return None
        return int(row[0])
