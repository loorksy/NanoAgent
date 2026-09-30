"""Tests for the layered prompt composer: snapshots, hygiene, and placeholder coverage."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from mokli.agent.prompt import composer
from mokli.agent.prompt.composer import (
    STATIC_LAYERS,
    TEAM_ROLE_COMMON,
    TOOL_CONTRACTS,
    WORKSPACE_LAYER,
    PromptContext,
    PromptRenderError,
    PromptSettings,
    compose_decision_prompt,
    compose_system_prompt,
    compose_team_role_prompt,
    placeholders_in,
    render_placeholders,
    render_tool_contracts,
    static_layer_values,
    team_role_names,
)

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_PROMPT_SNAPSHOTS") == "1"

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
WIRE_ID_RE = re.compile(r"(sess_|mokli:|websocket:|telegram:|whatsapp:|cli:|\bG\d{1,2}\b)")
FORBIDDEN_TERMS = ("lonora", "mokli 🐈", "🐈")

SAMPLE_TOOLS = (
    "get_gold_quote",
    "fetch_evidence",
    "run_trading_kernel",
    "get_live_recommendation",
    "capture_gold_chart",
    "run_trading_team",
    "mt5_list_symbols",
    "mt5_market",
    "mt5_propose_order",
    "mt5_confirm_order",
    "emit_result",
    "cron",
    "message",
)


def _all_prompt_files() -> list[Path]:
    root = composer.package_dir()
    return sorted(path for path in root.rglob("*.md"))


def _layer_files() -> list[Path]:
    return [composer.layers_dir() / name for name in STATIC_LAYERS]


def _ctx(language: str, with_tools: bool) -> PromptContext:
    return PromptContext(
        settings=PromptSettings(reply_language=language),
        channel="telegram" if with_tools else None,
        tool_names=list(SAMPLE_TOOLS) if with_tools else None,
        facts={"Permission level": "propose"} if with_tools else {},
    )


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("language", ["ar", "en", "auto"])
@pytest.mark.parametrize("with_tools", [True, False], ids=["with_tools", "without_tools"])
def test_composed_prompt_matches_snapshot(language: str, with_tools: bool) -> None:
    prompt = compose_system_prompt(_ctx(language, with_tools))
    name = f"system_{language}_{'tools' if with_tools else 'notools'}.md"
    path = SNAPSHOT_DIR / name
    if UPDATE_SNAPSHOTS or not path.exists():
        SNAPSHOT_DIR.mkdir(exist_ok=True)
        path.write_text(prompt + "\n", encoding="utf-8")
    assert prompt + "\n" == path.read_text(encoding="utf-8"), (
        f"snapshot {name} differs; rerun with UPDATE_PROMPT_SNAPSHOTS=1 after reviewing"
    )


def test_layer_order_is_fixed() -> None:
    prompt = compose_system_prompt(_ctx("auto", True))
    headings = ["# Mokli", "# Mission", "# Hard law", "# Tool contracts",
                "# Output contract", "# Behaviour", "# Runtime facts"]
    positions = [prompt.index(heading) for heading in headings]
    assert positions == sorted(positions)


def test_dynamic_sections_follow_static_layers_in_order() -> None:
    ctx = PromptContext(
        workspace="# Runtime and workspace\n\nRuntime: test",
        bootstrap="## AGENTS.md\n\nrules",
        project="# Current Project\n\nWorking directory: /tmp/p",
        memory="# Memory\n\n## Long-term Memory\nremembered",
        active_skills="# Active Skills\n\nskill body",
        skills_index="# Skills\n\nindex",
        archived_summary="[Archived Context Summary]\n\nsummary",
    )
    prompt = compose_system_prompt(ctx)
    markers = [
        "# Behaviour",
        "# Runtime and workspace",
        "## AGENTS.md",
        "# Current Project",
        "## Long-term Memory",
        "# Active Skills",
        "# Skills\n\nindex",
        "[Archived Context Summary]",
    ]
    positions = [prompt.index(marker) for marker in markers]
    assert positions == sorted(positions)
    assert "# Runtime facts" not in prompt


# ---------------------------------------------------------------------------
# Hygiene: language, persona, leakage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", _all_prompt_files(), ids=lambda p: p.name)
def test_prompt_files_are_english_and_single_persona(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert not ARABIC_RE.search(text), f"Arabic characters in {path.name}"
    lowered = text.lower()
    for term in FORBIDDEN_TERMS:
        assert term not in lowered, f"{term!r} in {path.name}"
    assert not WIRE_ID_RE.search(text), f"wire id in {path.name}"
    assert text.strip(), f"{path.name} is empty"


@pytest.mark.parametrize("language", ["ar", "en", "auto"])
def test_composed_prompt_has_no_arabic_or_second_persona(language: str) -> None:
    prompt = compose_system_prompt(_ctx(language, True))
    assert not ARABIC_RE.search(prompt)
    assert "lonora" not in prompt.lower()
    assert not WIRE_ID_RE.search(prompt)
    assert prompt.count("You are Mokli") == 1


def test_product_name_flows_into_every_persona_mention() -> None:
    ctx = PromptContext(settings=PromptSettings(product_name="GoldDesk"))
    prompt = compose_system_prompt(ctx)
    assert "Mokli" not in prompt
    assert prompt.startswith("# GoldDesk")
    assert "Present yourself as anything other than GoldDesk." in prompt


def test_layers_do_not_hard_code_thresholds() -> None:
    for path in _layer_files():
        text = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
        assert not re.search(r"\d+(\.\d+)?\s*%", text), f"percentage in {path.name}"
        assert not re.search(r"\d+(\.\d+)?\s*(pips?|points?|lots?)\b", text), path.name
    for name in ("20_mission.md", "30_hard_law.md"):
        text = re.sub(r"\s+", " ", (composer.layers_dir() / name).read_text(encoding="utf-8"))
        assert "configured risk parameters" in text, name


def test_no_sentence_is_duplicated_across_layers() -> None:
    seen: dict[str, str] = {}
    for path in _layer_files():
        text = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
        for sentence in re.split(r"(?<=[.!?])\s", text):
            key = sentence.strip().lower()
            if len(key) < 40 or "{" in key:
                continue
            assert key not in seen or seen[key] == path.name, (
                f"duplicated between {seen.get(key)} and {path.name}: {sentence!r}"
            )
            seen[key] = path.name


# ---------------------------------------------------------------------------
# Placeholders
# ---------------------------------------------------------------------------


def test_every_static_layer_placeholder_is_provided() -> None:
    provided = set(static_layer_values(PromptContext()))
    for path in _layer_files():
        missing = placeholders_in(path.read_text(encoding="utf-8")) - provided
        assert not missing, f"{path.name} needs {sorted(missing)}"


def test_workspace_layer_placeholders_are_documented() -> None:
    text = (composer.layers_dir() / WORKSPACE_LAYER).read_text(encoding="utf-8")
    assert placeholders_in(text) == {"runtime", "platform_notes", "workspace_paths"}


def test_decision_contract_placeholders() -> None:
    text = composer.decision_contract_template()
    assert placeholders_in(text) == {"product_name", "language"}


def test_team_role_placeholders_are_provided() -> None:
    allowed = {"product_name", "brief_language", "role_label"}
    for name in [TEAM_ROLE_COMMON, *team_role_names()]:
        text = composer.load_team_role(name)
        assert placeholders_in(text) <= allowed, name


def test_render_placeholders_is_strict_by_default_and_ignores_json_braces() -> None:
    assert render_placeholders('{"a":1} {name}', {"name": "x"}) == '{"a":1} x'
    with pytest.raises(PromptRenderError):
        render_placeholders("{missing}", {})
    assert render_placeholders("{missing}", {}, strict=False) == "{missing}"


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def test_language_and_tone_and_daily_wrap_settings_change_wording() -> None:
    en = compose_system_prompt(PromptContext(settings=PromptSettings(reply_language="en")))
    ar = compose_system_prompt(PromptContext(settings=PromptSettings(reply_language="ar")))
    auto = compose_system_prompt(PromptContext(settings=PromptSettings(reply_language="auto")))
    assert "Always reply in English" in en
    assert "Always reply in Arabic" in ar
    assert "Reply in the operator's language" in auto

    concise = compose_system_prompt(PromptContext(settings=PromptSettings(tone_profile="concise")))
    friendly = compose_system_prompt(PromptContext(settings=PromptSettings(tone_profile="friendly")))
    assert "Concise: lead with the conclusion" in concise
    assert "Approachable and warm" in friendly

    wrap = compose_system_prompt(PromptContext(settings=PromptSettings(daily_wrap_enabled=True)))
    assert "opted into a daily wrap" in wrap
    assert "daily wrap is disabled" in en


def test_unknown_settings_fall_back_to_defaults() -> None:
    prompt = compose_system_prompt(
        PromptContext(settings=PromptSettings(reply_language="fr", tone_profile="loud"))
    )
    assert "Reply in the operator's language" in prompt
    assert "Professional and measured" in prompt


def test_settings_from_agent_defaults_reads_defensively() -> None:
    class Defaults:
        product_name = "GoldDesk"
        reply_language = "ar"
        tone_profile = "concise"
        daily_wrap_enabled = True

    class Legacy:
        bot_name = "mokli"

    settings = PromptSettings.from_agent_defaults(Defaults())
    assert settings == PromptSettings("GoldDesk", "ar", "concise", True)
    assert PromptSettings.from_agent_defaults(Legacy()) == PromptSettings()
    assert PromptSettings.from_agent_defaults(None) == PromptSettings()


# ---------------------------------------------------------------------------
# Tool contracts
# ---------------------------------------------------------------------------


def test_tool_contract_table_renders_only_present_tools() -> None:
    table = render_tool_contracts(["get_gold_quote", "mt5_confirm_order"])
    assert "| `get_gold_quote` |" in table
    assert "| `mt5_confirm_order` |" in table
    assert "mt5_cancel_order" not in table
    assert "run_trading_team" not in table


def test_tool_contract_table_renders_everything_when_registry_unknown() -> None:
    table = render_tool_contracts(None)
    for contract in TOOL_CONTRACTS:
        for name in contract.tools:
            assert f"`{name}`" in table


def test_tool_contract_table_handles_empty_registry() -> None:
    table = render_tool_contracts([])
    assert "No platform tools are registered" in table


def test_answer_round_drops_the_tool_menu_and_keeps_policy() -> None:
    from mokli.agent.prompt.composer import messages_without_tool_menu
    from mokli.utils.helpers import estimate_message_tokens

    prompt = compose_system_prompt(PromptContext())
    original = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "هل أشتري الذهب؟"},
    ]
    sent = messages_without_tool_menu(original)
    assert "| Tool | Call when" in original[0]["content"]
    assert "| `get_gold_quote` |" not in sent[0]["content"]
    assert "No platform tools are registered" in sent[0]["content"]
    assert "## Execution permission levels" in sent[0]["content"]
    assert "`recommend`" in sent[0]["content"]
    assert sent[1] is original[1]
    before = estimate_message_tokens({"role": "system", "content": prompt})
    after = estimate_message_tokens({"role": "system", "content": sent[0]["content"]})
    assert before - after >= 700


def test_gold_price_contract_does_not_send_the_model_to_mt5_first() -> None:
    table = render_tool_contracts(["get_gold_quote", "mt5_market", "mt5_list_symbols"])
    gold = next(line for line in table.splitlines() if "`get_gold_quote`" in line)
    account = next(line for line in table.splitlines() if "`mt5_market`" in line)
    gold_when = gold.split("|")[2]
    account_when = account.split("|")[2]
    assert "when mt5_market was not used" not in gold
    assert "OANDA" in gold
    assert "MetaAPI" in gold
    assert "call mt5_market first" in gold
    assert "price" not in account_when
    assert "candle" not in account_when
    assert "execution account" in account_when
    assert "a gold price question" in gold_when
    assert "analysis candle source" in account


def test_tool_contract_names_are_unique() -> None:
    names = [name for contract in TOOL_CONTRACTS for name in contract.tools]
    assert len(names) == len(set(names))


def test_permission_levels_and_wording_are_in_the_contract_layer() -> None:
    prompt = compose_system_prompt(PromptContext())
    for level in ("`recommend`", "`propose`", "`execute`"):
        assert level in prompt
    assert '"I recommend …"' in prompt
    assert '"I propose … — confirm to execute"' in prompt
    assert '"Executed under your granted permission"' in prompt


def test_structured_output_policy_follows_emit_result_presence() -> None:
    with_tool = compose_system_prompt(PromptContext(tool_names=["emit_result"]))
    without = compose_system_prompt(PromptContext(tool_names=["get_gold_quote"]))
    assert "go through the `emit_result` tool" in with_tool
    assert "concise titled sections in prose" in without
    for result_type in ("market", "analysis", "scenarios", "risk", "decision", "approval",
                        "plan_status", "scorecard"):
        assert result_type in with_tool


# ---------------------------------------------------------------------------
# Decision and team prompts
# ---------------------------------------------------------------------------


def test_decision_prompt_inherits_hard_law_and_language() -> None:
    prompt = compose_decision_prompt(language="ar", product_name="GoldDesk")
    assert prompt.startswith("# Structured decision mode")
    assert "You are GoldDesk" in prompt
    assert "in natural Arabic" in prompt
    assert "# Hard law" in prompt
    assert prompt.index("# Structured decision mode") < prompt.index("# Hard law")
    assert "Respond with ONLY a JSON object" in prompt
    assert compose_decision_prompt(language="en").count("in natural English") == 1


def test_team_role_prompt_has_common_preamble_and_role_focus() -> None:
    prompt = compose_team_role_prompt("bull", product_name="GoldDesk", role_label="Bull Advocate")
    assert prompt.startswith("# GoldDesk — team specialist: Bull Advocate")
    assert "You never place an order" in prompt
    assert "STANCE line" in prompt
    assert "## Focus: the bull case" in prompt
    assert "Write in the operator's language" in prompt
    assert "Write in Arabic" in compose_team_role_prompt("bear", reply_language="ar")


def test_every_team_role_file_renders() -> None:
    names = team_role_names()
    assert {"bull", "bear", "risk", "macro", "structure", "liquidity", "lead"} <= set(names)
    for name in names:
        prompt = compose_team_role_prompt(name)
        assert "## Focus:" in prompt
        assert "{" not in prompt
