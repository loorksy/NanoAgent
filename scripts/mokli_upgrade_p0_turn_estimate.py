#!/usr/bin/env python3
"""Estimate first-turn request tokens without calling an LLM (P0 before/after helper).

Builds the same transcript the agent uses (system + user) and counts tool
definitions with ``component_tokens`` — the same breakdown as ``diagnostic.components``.

  python scripts/mokli_upgrade_p0_turn_estimate.py "مرحبا"
  python scripts/mokli_upgrade_p0_turn_estimate.py --compare "مرحبا" "حلل الذهب"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT = _SCRIPT_DIR.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mokli.agent.context import ContextBuilder, TranscriptInput  # noqa: E402
from mokli.agent.tools.context import ToolContext  # noqa: E402
from mokli.agent.tools.loader import ToolLoader  # noqa: E402
from mokli.agent.tools.registry import ToolRegistry  # noqa: E402
from mokli.agent.turn_diagnostics import component_tokens  # noqa: E402
from mokli.config.loader import load_config  # noqa: E402


def _load_registry(workspace: Path) -> ToolRegistry:
    config = load_config()
    registry = ToolRegistry()
    ctx = ToolContext(config=config.tools, workspace=str(workspace))
    ToolLoader().load(ctx, registry)
    return registry


def estimate_turn(
    message: str,
    *,
    workspace: Path,
    registry: ToolRegistry,
) -> dict[str, int]:
    builder = ContextBuilder(workspace)
    messages = builder.build_transcript(
        TranscriptInput(history=[], current_message=message),
        tool_names=list(registry.tool_names),
    )
    tools = registry.get_definitions()
    parts = component_tokens(messages, tools)
    return {**parts, "tools_registered": len(registry.tool_names)}


def _print_line(message: str, parts: dict[str, int]) -> None:
    preview = message if len(message) <= 40 else message[:37] + "..."
    print(
        f"msg={preview!r} final={parts['final']} system={parts['system']} "
        f"conversation={parts['conversation']} tool_defs={parts['tool_definitions']} "
        f"tools_registered={parts.get('tools_registered', '—')}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("messages", nargs="*", help="User messages to estimate")
    parser.add_argument(
        "--compare",
        nargs="+",
        metavar="MSG",
        help="Print two or more messages and a final delta line",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Agent workspace for ContextBuilder (default: cwd)",
    )
    args = parser.parse_args()
    msgs = args.compare if args.compare else args.messages
    if not msgs:
        parser.error("provide at least one message or --compare")

    workspace = args.workspace.expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    registry = _load_registry(workspace)
    results: list[tuple[str, dict[str, int]]] = []
    for msg in msgs:
        parts = estimate_turn(msg, workspace=workspace, registry=registry)
        results.append((msg, parts))
        _print_line(msg, parts)

    if len(results) >= 2:
        first_final = results[0][1]["final"]
        last_final = results[-1][1]["final"]
        print(f"delta_final={last_final - first_final} (last minus first)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
