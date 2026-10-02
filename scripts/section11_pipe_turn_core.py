#!/usr/bin/env python3
"""Run one Mokli UI pipe turn against localhost Agent API and log gateway JSONL (§11 row 12)."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


def _load_pipe_module(pipe_path: Path):
    spec = importlib.util.spec_from_file_location("section11_mokli_pipe", pipe_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load pipe module from {pipe_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def _run_turn(
    *,
    install: Path,
    out_name: str,
    prompt: str,
    model_override: str | None,
) -> None:
    pipe_path = install / "deploy/mokliui/functions/mokli_pipe.py"
    if not pipe_path.is_file():
        raise FileNotFoundError(pipe_path)

    token_path = install / ".mokli/workspace/agent_api/admin_token"
    if not token_path.is_file():
        raise FileNotFoundError(token_path)
    token = token_path.read_text(encoding="utf-8").strip()

    event_dir = install / "section11-events"
    event_dir.mkdir(parents=True, exist_ok=True)
    out_path = event_dir / out_name
    out_path.write_text("", encoding="utf-8")

    pipe_mod = _load_pipe_module(pipe_path)

    class _LoggingPipe(pipe_mod.Pipe):
        async def _handle_event(self, event, turn, gateway, emitter, caller):  # type: ignore[no-untyped-def]
            with out_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            return await super()._handle_event(event, turn, gateway, emitter, caller)

    pipe = _LoggingPipe()
    pipe.valves = pipe.Valves(
        GATEWAY_URL="http://127.0.0.1:8766",
        GATEWAY_TOKEN=token,
        DEFAULT_LOCALE="ar",
        SHOW_TIMELINE=True,
        SHOW_DIAGNOSTICS=True,
        REQUEST_TIMEOUT=900,
    )

    selector = "mokli"
    if model_override:
        selector = f"mokli.{model_override}"

    body: dict[str, Any] = {
        "model": selector,
        "messages": [{"role": "user", "content": prompt}],
    }
    chat_id = f"section11-{out_name.removesuffix('.jsonl')}"
    metadata = {"chat_id": chat_id, "variables": {"{{USER_LANGUAGE}}": "ar"}}

    async def _noop_emit(_event: dict[str, object]) -> None:
        return None

    async def _noop_call(_event: dict[str, object]) -> bool:
        return True

    user = {"id": "section11", "name": "Operator", "role": "admin"}

    async for _chunk in pipe.pipe(body, user, metadata, _noop_emit, _noop_call):
        pass

    if not out_path.stat().st_size:
        raise RuntimeError(f"pipe turn produced empty JSONL: {out_path}")

    extract = install / "scripts/mokli_upgrade_diagnostic_extract.py"
    if extract.is_file():
        import subprocess

        proc = subprocess.run(
            [sys.executable, str(extract), "--file", str(out_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.stdout:
            print(proc.stdout.rstrip())
        if proc.returncode != 0 and proc.stderr:
            print(proc.stderr.rstrip(), file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="§11 headless Mokli pipe turn (gateway JSONL).")
    parser.add_argument("install", type=Path, help="Mokli install root (e.g. /opt/nanoagent)")
    parser.add_argument("out_name", help="JSONL filename under section11-events/")
    parser.add_argument("prompt", help="User message text")
    args = parser.parse_args()

    model_override = os.environ.get("MOKLI_SECTION11_MODEL", "").strip() or None
    try:
        asyncio.run(
            _run_turn(
                install=args.install.resolve(),
                out_name=args.out_name,
                prompt=args.prompt,
                model_override=model_override,
            )
        )
    except Exception as exc:
        print(f"section11 pipe turn failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
