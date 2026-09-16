"""Gold encyclopedia skills: ids, English-only refs, valid frontmatter."""

from __future__ import annotations

import re
from pathlib import Path

from nanobot.agent.skills import SkillsLoader, parse_skill_metadata, valid_skill_metadata

SKILLS_ROOT = Path("nanobot/skills")
_ARABIC = re.compile(r"[\u0600-\u06FF]")
_SECTION_CODE = re.compile(r"\bS[1-9](?:\.\d+)?\b")
_GATE_WIRE_ID = re.compile(r"\bG(?:[1-9]|1[0-9]|20)\b")
_SPEC_SECTION = re.compile(r"Spec\s*[§0-9]", re.I)

_ENCYCLOPEDIA_SKILLS = (
    "technical-analysis",
    "macro-radar",
    "risk-guardrails",
    "news-volatility-protocol",
    "xauusd-playbook",
    "mt5-execution",
    "memory-review",
    "security-resilience",
    "multi-tasking-scenarios",
)


def _ids(prefix: str, count: int) -> set[str]:
    width = 3
    return {f"{prefix}-{i:0{width}d}" for i in range(1, count + 1)}


def test_encyclopedia_skills_have_valid_frontmatter() -> None:
    for name in _ENCYCLOPEDIA_SKILLS:
        text = (SKILLS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")
        meta = parse_skill_metadata(text)
        assert meta is not None, name
        assert valid_skill_metadata(meta, name), name


def test_builtin_loader_lists_encyclopedia_skills(tmp_path: Path) -> None:
    loader = SkillsLoader(tmp_path, builtin_skills_dir=SKILLS_ROOT)
    names = {entry["name"] for entry in loader.list_skills(filter_unavailable=False)}
    assert set(_ENCYCLOPEDIA_SKILLS) <= names
    assert "gold-trading" in names


def test_playbook_news_and_candle_ids_are_complete() -> None:
    playbook = "".join(
        path.read_text(encoding="utf-8")
        for path in sorted((SKILLS_ROOT / "xauusd-playbook" / "references").glob("playbook-*.md"))
    )
    news = (SKILLS_ROOT / "news-volatility-protocol" / "references" / "news-100.md").read_text(
        encoding="utf-8"
    )
    candles = (
        SKILLS_ROOT / "news-volatility-protocol" / "references" / "news-candles-100.md"
    ).read_text(encoding="utf-8")
    found_p = set(re.findall(r"^### (P-\d{3}) ", playbook, re.MULTILINE))
    found_n = set(re.findall(r"^### (N-\d{3}) ", news, re.MULTILINE))
    found_c = set(re.findall(r"^### (C-\d{3}) ", candles, re.MULTILINE))
    assert found_p == _ids("P", 200)
    assert found_n == _ids("N", 100)
    assert found_c == _ids("C", 100)
    assert "EXCLUDED" in playbook
    assert "P-182" in playbook


def test_encyclopedia_skill_bodies_and_references_are_english() -> None:
    for name in _ENCYCLOPEDIA_SKILLS:
        skill_dir = SKILLS_ROOT / name
        for path in [skill_dir / "SKILL.md", *sorted((skill_dir / "references").rglob("*.md"))]:
            text = path.read_text(encoding="utf-8")
            assert _ARABIC.search(text) is None, f"Arabic in {path}"
    gold = SKILLS_ROOT / "gold-trading" / "SKILL.md"
    proactive = SKILLS_ROOT / "trading-proactive" / "SKILL.md"
    assert _ARABIC.search(gold.read_text(encoding="utf-8")) is None
    assert _ARABIC.search(proactive.read_text(encoding="utf-8")) is None


def test_quick_historical_replay_is_excluded() -> None:
    text = (SKILLS_ROOT / "memory-review" / "references" / "section-5-memory.md").read_text(
        encoding="utf-8"
    )
    assert "Quick replay" in text
    assert "EXCLUDED" in text
    coverage = (SKILLS_ROOT / "gold-trading" / "references" / "coverage.md").read_text(
        encoding="utf-8"
    )
    assert "Quick historical replay" in coverage
    assert "backtest" in coverage.lower()


def test_coverage_table_mentions_hitl_exclusion() -> None:
    coverage = (SKILLS_ROOT / "gold-trading" / "references" / "coverage.md").read_text(
        encoding="utf-8"
    )
    assert "P-182" in coverage
    assert "FEATURE-01" in coverage
    assert "position sizing" in coverage
    assert "Minimum reward-to-risk" in coverage


def test_skill_markdown_uses_names_not_section_or_gate_codes() -> None:
    for path in sorted(SKILLS_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert _SECTION_CODE.search(text) is None, f"section code leftover in {path}"
        assert _GATE_WIRE_ID.search(text) is None, f"gate wire id leftover in {path}"
        assert _SPEC_SECTION.search(text) is None, f"spec-section leftover in {path}"
        assert "R:R" not in text, f"R:R leftover in {path}"
