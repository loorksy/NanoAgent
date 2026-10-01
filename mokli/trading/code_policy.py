"""Static review of model-written Python before any sandbox process starts.

The review is a gate, not a suggestion. ``run_python`` refuses to spawn when
this module raises. It does not try to rewrite the program into a safe one.
"""

from __future__ import annotations

import ast

MAX_CODE_CHARS = 12_000

# Modules the sandbox preloads. Anything else is a policy failure.
ALLOWED_MODULES = frozenset(
    {
        "math",
        "statistics",
        "json",
        "decimal",
        "datetime",
        "collections",
        "itertools",
        "functools",
        "re",
    }
)

# Names that would escape a restricted ``__builtins__`` or touch the host.
_BANNED_CALLS = frozenset(
    {
        "exec",
        "eval",
        "compile",
        "open",
        "input",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "dir",
        "breakpoint",
        "help",
        "memoryview",
        "classmethod",
        "staticmethod",
        "property",
        "super",
        "type",
        "object",
        "bytes",
        "bytearray",
        "__import__",
    }
)

_BANNED_ATTRS = frozenset(
    {
        "system",
        "popen",
        "spawn",
        "execl",
        "execv",
        "remove",
        "unlink",
        "rmdir",
        "connect",
        "bind",
        "listen",
        "send",
        "sendall",
        "recv",
    }
)

# Substrings that mean the program is trying to reach the broker, credentials,
# or the host network. Matched case-insensitively against the raw source so a
# string that never becomes an import still fails the gate.
_BANNED_SNIPPETS = (
    "metatrader",
    "meta trader",
    "order_send",
    "ordersend",
    "mt5_password",
    "mt5_login",
    "mt5_server",
    "mt5_host",
    "import mt5",
    "import socket",
    "import urllib",
    "import http",
    "import requests",
    "import httpx",
    "import subprocess",
    "import ctypes",
    "import os",
    "import sys",
    "import shutil",
    "import pathlib",
    "import pickle",
    "import importlib",
    "169.254.169.254",
    "/etc/passwd",
    "/etc/shadow",
    ".env",
)


class CodePolicyError(ValueError):
    """The program is not allowed to run."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def review_python(source: str) -> None:
    """Raise ``CodePolicyError`` when *source* must not be executed."""
    text = source if isinstance(source, str) else ""
    if not text.strip():
        raise CodePolicyError("code is empty")
    if len(text) > MAX_CODE_CHARS:
        raise CodePolicyError(f"code exceeds {MAX_CODE_CHARS} characters")
    lowered = text.lower()
    for snippet in _BANNED_SNIPPETS:
        if snippet in lowered:
            raise CodePolicyError(f"code mentions a blocked capability: {snippet}")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise CodePolicyError(f"code is not valid Python: {exc.msg}") from exc
    _walk(tree)


def _walk(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.ClassDef, ast.AsyncFunctionDef, ast.With, ast.AsyncWith, ast.Global, ast.Nonlocal),
        ):
            raise CodePolicyError(f"{type(node).__name__} is not allowed")
        if isinstance(node, ast.Attribute) and _banned_attr(node.attr):
            raise CodePolicyError(f"attribute {node.attr} is not allowed")
        if isinstance(node, ast.Name) and (node.id.startswith("_") or node.id in _BANNED_CALLS):
            raise CodePolicyError(f"name {node.id} is not allowed")
        if isinstance(node, ast.Call):
            _review_call(node)
        if isinstance(node, ast.Import):
            for alias in node.names:
                _require_module(alias.name)
        if isinstance(node, ast.ImportFrom):
            if node.level:
                raise CodePolicyError("relative imports are not allowed")
            if node.module is None:
                raise CodePolicyError("bare imports are not allowed")
            _require_module(node.module)
            for alias in node.names:
                if alias.name == "*":
                    raise CodePolicyError("star imports are not allowed")


def _banned_attr(name: str) -> bool:
    return name.startswith("_") or name in _BANNED_ATTRS


def _review_call(node: ast.Call) -> None:
    func = node.func
    if isinstance(func, ast.Name) and func.id in _BANNED_CALLS:
        raise CodePolicyError(f"call to {func.id} is not allowed")
    if isinstance(func, ast.Attribute) and _banned_attr(func.attr):
        raise CodePolicyError(f"call to {func.attr} is not allowed")


def _require_module(name: str) -> None:
    root = name.split(".", 1)[0]
    if root not in ALLOWED_MODULES:
        raise CodePolicyError(f"import of {root} is not allowed")
