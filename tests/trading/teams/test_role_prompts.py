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
    assert "You never place an order" in prompt
    assert "STANCE line" in prompt


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


def test_decision_review_asks_for_a_stance_the_risk_prompt_allows() -> None:
    from mokli.trading.teams.runtime import load_preset

    preset = load_preset("gold_decision_review")
    assert [task.id for task in preset.tasks] == [
        "task-technical",
        "task-macro",
        "task-trend",
        "task-risk",
        "task-review",
    ]
    for task in preset.tasks:
        assert "STANCE:" in task.prompt_template
    risk = role_system_prompt("Risk Officer", system_prompt="role:risk")
    assert "STANCE: wait" in risk
    assert "never place an order" in risk
    assert "You never choose buy or sell" not in risk
    review = role_system_prompt("Review Analyst", system_prompt="role:lead")
    assert "unless the task asks for one STANCE line" in review
    assert "not an order" in review
    assert "Do not choose a direction, do not propose levels" not in review
    committee = role_system_prompt("Lead Analyst", system_prompt="role:lead")
    assert "unless the task asks for one STANCE line" in committee
    from mokli.utils.helpers import estimate_prompt_tokens

    old_lead = (
        "## Focus: lead synthesis\n\n"
        "Synthesise the upstream specialist briefs into one neutral, evidence-ordered summary for the\n"
        "structured decision call. Rank the points of agreement, then the conflicts, then what remains\n"
        "unknown. Attribute each point to the brief it came from and drop anything a brief asserted\n"
        "without evidence. Do not choose a direction, do not propose levels, and do not smooth over a\n"
        "genuine conflict between briefs.\n"
    )
    new_lead = (
        Path(role_prompts.__file__).resolve().parents[2]
        / "agent"
        / "prompt"
        / "team_roles"
        / "lead.md"
    ).read_text(encoding="utf-8")
    before = estimate_prompt_tokens([{"role": "user", "content": old_lead}])
    after = estimate_prompt_tokens([{"role": "user", "content": new_lead}])
    print(f"LEAD_PROMPT before={before} after={after}")
    assert after > before
    by_id = {task.id: task for task in preset.tasks}
    assert by_id["task-risk"].input_from == {
        "technical": "task-technical",
        "macro": "task-macro",
        "trend": "task-trend",
    }
    assert by_id["task-review"].input_from == {
        "technical": "task-technical",
        "macro": "task-macro",
        "trend": "task-trend",
        "risk": "task-risk",
    }
    from mokli.trading.teams.runtime import brief_for_upstream

    technical = ("level " * 200) + "\nSTANCE: sell"
    summaries = {
        "task-technical": technical,
        "task-macro": "STANCE: wait",
        "task-trend": "STANCE: buy",
        "task-risk": "conflict on the hour\nSTANCE: wait",
    }
    risk_upstream = "\n".join(
        f"{key}: {brief_for_upstream(summaries[src])}"
        for key, src in by_id["task-risk"].input_from.items()
    )
    review_upstream = "\n".join(
        f"{key}: {brief_for_upstream(summaries[src])}"
        for key, src in by_id["task-review"].input_from.items()
    )
    assert "STANCE: sell" in risk_upstream
    assert "candles" not in risk_upstream
    assert len(brief_for_upstream(technical)) < len(technical)
    assert "STANCE: sell" in review_upstream
    assert "STANCE: wait" in review_upstream
    assert "STANCE: buy" in review_upstream


def test_role_files_cover_the_legacy_role_set() -> None:
    assert {"bull", "bear", "risk", "macro", "structure", "liquidity", "lead", "news"} <= set(
        list_role_files()
    )
