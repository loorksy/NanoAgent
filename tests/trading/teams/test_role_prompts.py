"""Team role prompts are loaded from ``mokli/agent/prompt/team_roles`` for every preset."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from mokli.trading.teams import role_prompts
from mokli.trading.teams.role_prompts import (
    list_role_files,
    resolve_role_file,
    role_file_for,
    role_system_prompt,
)

PRESETS_DIR = Path(role_prompts.__file__).parent / "presets"
ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def _preset_agents() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for path in sorted(PRESETS_DIR.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        for agent in raw.get("agents", []):
            rows.append((path.stem, str(agent["role"]), str(agent.get("system_prompt", ""))))
    return rows


@pytest.mark.parametrize(("preset", "role", "system_prompt"), _preset_agents())
def test_every_preset_role_gets_non_empty_english_prompt(
    preset: str, role: str, system_prompt: str
) -> None:
    prompt = role_system_prompt(role, system_prompt=system_prompt)
    assert prompt.strip(), f"{preset}:{role}"
    assert not ARABIC_RE.search(prompt)
    assert "lonora" not in prompt.lower()
    assert "{" not in prompt
    assert f"team specialist: {role}" in prompt
    assert "## Focus:" in prompt
    assert "You never choose buy or sell" in prompt


@pytest.mark.parametrize(("preset", "role", "system_prompt"), _preset_agents())
def test_preset_system_prompt_fields_reference_existing_role_files(
    preset: str, role: str, system_prompt: str
) -> None:
    assert system_prompt.startswith("role:"), f"{preset}:{role} must reference a role file"
    stem = system_prompt.removeprefix("role:")
    assert stem in list_role_files(), f"{preset}:{role} -> {stem}"
    assert resolve_role_file(role, system_prompt) == stem


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("Macro Analyst", "macro"),
        ("Structure Analyst", "structure"),
        ("Liquidity Analyst", "liquidity"),
        ("Risk Officer", "risk"),
        ("Risk Manager", "risk"),
        ("Lead Analyst", "lead"),
        ("Bull Advocate", "bull"),
        ("Bear Advocate", "bear"),
        ("News Scanner", "news"),
        ("Event Analyst", "event"),
        ("Scenario Planner", "scenario"),
        ("H1 Analyst", "timeframe"),
        ("D1 Analyst", "timeframe"),
        ("MTF Synthesizer", "mtf_synthesizer"),
        ("Committee Chair", "lead"),
        ("", "lead"),
        ("Something Unknown", "lead"),
    ],
)
def test_role_label_keyword_mapping(role: str, expected: str) -> None:
    assert role_file_for(role) == expected


def test_unknown_reference_falls_back_to_label_mapping() -> None:
    assert resolve_role_file("Bear Advocate", "role:does_not_exist") == "bear"
    assert resolve_role_file("Bear Advocate", "Argue against the setup.") == "bear"


def test_language_and_product_name_are_injected() -> None:
    prompt = role_system_prompt("Bull Advocate", product_name="GoldDesk", reply_language="ar")
    assert prompt.startswith("# GoldDesk — team specialist: Bull Advocate")
    assert "Write in Arabic" in prompt
    default = role_system_prompt("Bull Advocate")
    assert "You are Mokli" in default
    assert "Write in the operator's language" in default


def test_role_files_cover_the_legacy_role_set() -> None:
    assert {"bull", "bear", "risk", "macro", "structure", "liquidity", "lead", "news"} <= set(
        list_role_files()
    )
