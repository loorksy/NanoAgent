"""FEATURE-07 — FastDTW pattern matcher with a tiny built-in fallback."""

from __future__ import annotations

from dataclasses import dataclass

TEMPLATES: dict[str, list[float]] = {
    "accumulation": [0.4, 0.42, 0.41, 0.43, 0.42, 0.45, 0.44, 0.46, 0.5, 0.55],
    "distribution": [0.7, 0.72, 0.68, 0.7, 0.65, 0.66, 0.6, 0.55, 0.5, 0.42],
    "turtle_soup": [0.5, 0.55, 0.62, 0.7, 0.78, 0.6, 0.48, 0.42, 0.45, 0.52],
    "v_reversal": [0.8, 0.7, 0.55, 0.4, 0.28, 0.35, 0.5, 0.65, 0.78, 0.82],
}


def _normalize(series: list[float]) -> list[float]:
    if not series:
        return []
    lo = min(series)
    hi = max(series)
    span = hi - lo or 1.0
    return [(x - lo) / span for x in series]


def _dtw(a: list[float], b: list[float]) -> float:
    try:
        import numpy as np
        from fastdtw import fastdtw

        dist, _ = fastdtw(np.array(a), np.array(b))
        return float(dist)
    except Exception:
        n, m = len(a), len(b)
        inf = float("inf")
        dp = [[inf] * (m + 1) for _ in range(n + 1)]
        dp[0][0] = 0.0
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                cost = abs(a[i - 1] - b[j - 1])
                dp[i][j] = cost + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
        return dp[n][m]


@dataclass(frozen=True)
class PatternMatch:
    name: str
    distance: float
    confidence: float


def match_pattern(closes: list[float], *, templates: dict[str, list[float]] | None = None) -> PatternMatch:
    series = _normalize(closes[-30:])
    best = PatternMatch("none", float("inf"), 0.0)
    for name, tmpl in (templates or TEMPLATES).items():
        dist = _dtw(series, _normalize(tmpl))
        # Map small DTW distance to a 0-1 confidence.
        conf = max(0.0, 1.0 - dist / max(len(series), 1))
        if conf > best.confidence:
            best = PatternMatch(name, dist, conf)
    return best
