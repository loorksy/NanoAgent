"""Optional extras without try/except around imports."""

from __future__ import annotations

import importlib.util


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None
