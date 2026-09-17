"""FEATURE-06 — local vector playbook (Chroma/Lance if present, otherwise bag-of-words)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from nanobot.trading.intel.optional_deps import module_available

_TOKEN = re.compile(r"[a-z0-9]+")

SEED_SCENARIOS = [
    "false break of asian high plus M15 structure shift plus overbought plus weak dollar",
    "london sweep of asian low then bullish engulfing into discount FVG",
    "NFP spike wick then range reclaim and DXY breakdown",
    "FOMC hold then hawkish presser — gold sells off with rising yields",
    "geopolitical shock safe-haven bid while DXY also rises — decoupling",
    "equal highs raid then CHoCH down and bearish FVG fill",
    "H4 200 EMA hold as demand, H1 BOS up, M15 OTE entry",
    "CPI hot surprise — yields up, gold dump, wait 15 minutes then short retest",
    "CPI cool surprise — yields down, gold squeeze, buy first pullback",
    "dead asian range under 70 points — stand aside until London open",
]


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _bow(text: str) -> dict[str, float]:
    counts: dict[str, float] = {}
    for tok in _tokens(text):
        counts[tok] = counts.get(tok, 0.0) + 1.0
    norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
    return {k: v / norm for k, v in counts.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) & set(b)
    return sum(a[k] * b[k] for k in keys)


@dataclass(frozen=True)
class PlaybookMatch:
    scenario: str
    score: float


class VectorPlaybook:
    def __init__(self, scenarios: list[str] | None = None) -> None:
        self.scenarios = list(scenarios or SEED_SCENARIOS)
        self._vectors = [_bow(s) for s in self.scenarios]
        self._chroma = None
        self.backend = "bag_of_words"
        if module_available("chromadb"):
            import chromadb

            try:
                client = chromadb.Client()
                col = client.get_or_create_collection("gold-playbook")
                if col.count() == 0:
                    col.add(
                        ids=[str(i) for i in range(len(self.scenarios))],
                        documents=self.scenarios,
                    )
                self._chroma = col
                self.backend = "chromadb"
            except Exception:
                self._chroma = None
                self.backend = "bag_of_words"
        elif module_available("lancedb"):
            self.backend = "lancedb_unavailable_adapter"

    def add(self, scenario: str) -> None:
        self.scenarios.append(scenario)
        self._vectors.append(_bow(scenario))

    def query(self, context: str, *, k: int = 3) -> list[PlaybookMatch]:
        if self._chroma is not None:
            result = self._chroma.query(query_texts=[context], n_results=k)
            docs = (result.get("documents") or [[]])[0]
            dists = (result.get("distances") or [[]])[0]
            out: list[PlaybookMatch] = []
            for doc, dist in zip(docs, dists, strict=False):
                score = max(0.0, 1.0 - float(dist))
                out.append(PlaybookMatch(str(doc), score))
            if out:
                return out
        q = _bow(context)
        ranked = sorted(
            (PlaybookMatch(s, _cosine(q, v)) for s, v in zip(self.scenarios, self._vectors, strict=True)),
            key=lambda m: m.score,
            reverse=True,
        )
        return ranked[:k]
