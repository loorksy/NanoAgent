"""Fail if new user-visible copy is hard-coded outside i18n.py."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path("nanobot")
WEB_RISK = Path("webui/src/components/trading/RiskParametersSettings.tsx")

SCAN_DIRS = [
    ROOT / "trading" / "gates",
    ROOT / "webui",
]
SCAN_FILES = [
    ROOT / "trading" / "mt5_execution.py",
    ROOT / "trading" / "mt5_metaapi.py",
    ROOT / "trading" / "broker_result.py",
    WEB_RISK,
]

# Wire values and i18n keys are allowed; operator sentences are not.
_SENTENCE = re.compile(r"[A-Za-z]{3,}.*\s+[A-Za-z]{3,}")
_KEY_LIKE = re.compile(r"^(gate|mt5|risk|price|lesson|card|followup|news)\.[a-z0-9_.]+$")


def test_trading_user_strings_live_in_i18n() -> None:
    offenders: list[str] = []
    files: list[Path] = list(SCAN_FILES)
    for folder in SCAN_DIRS:
        files.extend(folder.rglob("*.py"))
    for path in files:
        if path.suffix == ".py":
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            docstring_ids: set[int] = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if (
                        node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)
                    ):
                        docstring_ids.add(id(node.body[0].value))
            for child in ast.walk(tree):
                if not isinstance(child, ast.Constant) or not isinstance(child.value, str):
                    continue
                if id(child) in docstring_ids:
                    continue
                text = child.value.strip()
                if len(text) < 16:
                    continue
                if _KEY_LIKE.match(text):
                    continue
                if "http" in text or text.startswith("nanobot."):
                    continue
                looks_sentence = bool(re.search(r"[.!?]$", text)) or " must " in text.lower()
                if not looks_sentence:
                    continue
                if not _SENTENCE.search(text):
                    continue
                offenders.append(f"{path}:{getattr(child, 'lineno', 0)}:{text[:80]}")
        elif path.suffix == ".tsx":
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r">([^<{][^<]{8,})<", text):
                blob = match.group(1).strip()
                if _SENTENCE.search(blob) and "payload." not in blob:
                    offenders.append(f"{path}:jsx:{blob[:80]}")
            for match in re.finditer(r"(['\"`])([A-Z][^'\"`]{12,})\1", text):
                blob = match.group(2)
                if re.search(r"(must be a number|Risk Parameters|Feature toggles|Saving|Loading)", blob):
                    offenders.append(f"{path}:literal:{blob[:80]}")
    assert offenders == []
