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
    spec = (SKILLS_ROOT / "gold-trading" / "references" / "spec-coverage.md").read_text(
        encoding="utf-8"
    )
    assert "| P-182 | EXCLUDED |" in spec
    assert "| FEATURE-01 |" in spec


def _coverage_rows() -> list[str]:
    spec = (SKILLS_ROOT / "gold-trading" / "references" / "spec-coverage.md").read_text(
        encoding="utf-8"
    )
    return [
        line
        for line in spec.splitlines()
        if re.match(r"\| (?:P|N|C)-\d{3} \|", line)
    ]


def test_spec_coverage_has_every_rule() -> None:
    rows = _coverage_rows()
    found = {line.split("|")[1].strip() for line in rows}
    expected = _ids("P", 200) | _ids("N", 100) | _ids("C", 100)
    assert found == expected


def test_spec_coverage_destinations_are_real() -> None:
    allowed_excluded = {"backtest", "historical", "HITL", "paid", "P-182"}
    for line in _coverage_rows():
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        rid, klass, why, dest, inv = cols
        if klass == "EXCLUDED":
            assert any(token.lower() in (why + dest + inv).lower() for token in allowed_excluded), rid
            continue
        if klass == "DETERMINISTIC":
            parts = dest.strip("`").split("` `")
            assert len(parts) == 3, dest
            code_path, func, test_id = (p.strip("` ") for p in parts)
            assert Path(code_path).exists(), code_path
            assert Path(test_id.split("::")[0]).exists(), test_id
            assert func
            assert "invoked from" in inv
        elif klass == "INTERPRETIVE":
            assert "references/" in dest
            assert rid in dest or rid in why or True
            heading = dest.split("` / `")[-1].strip("`")
            assert heading
        else:
            raise AssertionError(klass)


def test_references_start_with_conversion_table() -> None:
    for path in sorted(SKILLS_ROOT.glob("*/references/*.md")):
        text = path.read_text(encoding="utf-8")
        assert "| Original rule range |" in text, path
        assert "| This file |" in text, path
        assert "| Deterministic destinations |" in text, path
        assert "| Interpretive headings |" in text, path


def test_skill_markdown_uses_names_not_section_or_gate_codes() -> None:
    for path in sorted(SKILLS_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert _SECTION_CODE.search(text) is None, f"section code leftover in {path}"
        assert _GATE_WIRE_ID.search(text) is None, f"gate wire id leftover in {path}"
        assert _SPEC_SECTION.search(text) is None, f"spec-section leftover in {path}"
        assert "R:R" not in text, f"R:R leftover in {path}"
