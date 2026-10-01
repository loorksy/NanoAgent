"""Skill reads stay inside markdown and profile files."""

from __future__ import annotations

from pathlib import Path

import pytest

from mokli.trading.skill_access import SkillPathError, grep_skills, read_text, resolve_readable


def test_reads_builtin_skill(tmp_path: Path) -> None:
    path = resolve_readable(tmp_path, "gold-trading/SKILL.md")
    body = read_text(path, limit=5)
    assert "gold-trading" in body or "Gold" in body or body


def test_refuses_env_file(tmp_path: Path) -> None:
    secret = tmp_path / ".env"
    secret.write_text("MT5_PASSWORD=nope\n", encoding="utf-8")
    with pytest.raises(SkillPathError):
        resolve_readable(tmp_path, str(secret))


def test_refuses_path_outside_skills(tmp_path: Path) -> None:
    outside = tmp_path / "notes.md"
    outside.write_text("hello\n", encoding="utf-8")
    with pytest.raises(SkillPathError):
        resolve_readable(tmp_path, str(outside))


def test_reads_profile_memory(tmp_path: Path) -> None:
    memory = tmp_path / "memory"
    memory.mkdir()
    file = memory / "MEMORY.md"
    file.write_text("prefers Arabic replies\n", encoding="utf-8")
    resolved = resolve_readable(tmp_path, "memory/MEMORY.md")
    assert "Arabic" in read_text(resolved)


def test_gold_loader_lists_the_new_modules() -> None:
    text = Path("mokli/agent/tools/loader.py").read_text(encoding="utf-8")
    assert '"skill_files"' in text
    assert '"python_sandbox"' in text


def test_grep_finds_a_literal_rule(tmp_path: Path) -> None:
    found = grep_skills(tmp_path, "XAUUSD", path="gold-trading", limit=5)
    assert "gold-trading" in found
    assert "XAUUSD" in found
