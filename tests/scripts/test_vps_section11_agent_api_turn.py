"""vps_section11_agent_api_turn.sh passes prompts with shell metacharacters safely."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "vps_section11_agent_api_turn.sh"


def test_turn_script_base64_encodes_prompt() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "PROMPT_B64" in text
    assert "base64 -d" in text
    assert "sys.argv[1]" not in text
