"""FEATURE-09 — local sentiment via Ollama (optional) with a keyword fallback."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx

HAWKISH = ("hike", "restrictive", "inflation remains", "higher for longer", "tightening")
DOVISH = ("cut", "easing", "slowdown", "downside risks", "employment cooling")


@dataclass(frozen=True)
class SentimentResult:
    bias: str
    confidence: float
    reason: str
    source: str


def _keyword_fallback(text: str) -> SentimentResult:
    low = text.lower()
    hawk = sum(1 for w in HAWKISH if w in low)
    dove = sum(1 for w in DOVISH if w in low)
    if hawk > dove:
        return SentimentResult("BEARISH_GOLD", min(1.0, 0.4 + 0.15 * hawk), "hawkish keywords", "fallback")
    if dove > hawk:
        return SentimentResult("BULLISH_GOLD", min(1.0, 0.4 + 0.15 * dove), "dovish keywords", "fallback")
    return SentimentResult("NEUTRAL", 0.3, "no dominant tone", "fallback")


async def classify_sentiment(text: str, *, model: str | None = None) -> SentimentResult:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = model or os.environ.get("OLLAMA_SENTIMENT_MODEL", "qwen2.5:3b")
    prompt = (
        "Classify the central-bank or macro text for gold. "
        'Return JSON only: {"bias":"BULLISH_GOLD"|"BEARISH_GOLD"|"NEUTRAL",'
        '"confidence":0-1,"reason":"short"}.\n\n'
        f"TEXT:\n{text[:4000]}"
    )
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                f"{host}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
            )
            resp.raise_for_status()
            payload = resp.json()
            raw = payload.get("response") or "{}"
            data = json.loads(raw) if isinstance(raw, str) else raw
            bias = str(data.get("bias") or "NEUTRAL")
            if bias not in {"BULLISH_GOLD", "BEARISH_GOLD", "NEUTRAL"}:
                bias = "NEUTRAL"
            return SentimentResult(
                bias=bias,
                confidence=float(data.get("confidence") or 0.5),
                reason=str(data.get("reason") or ""),
                source="ollama",
            )
    except Exception:
        return _keyword_fallback(text)
