"""Repository-wide pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="session")
def _isolated_git_config(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Keep git-backed tests hermetic.

    Developer machines may carry a global git config with commit signing,
    credential helpers, or hooks. Both the ``git`` CLI and dulwich honour
    ``GIT_CONFIG_GLOBAL`` / ``GIT_CONFIG_NOSYSTEM``, so pointing them at an
    empty config makes repository fixtures behave like a clean CI runner.
    """
    monkeypatch = pytest.MonkeyPatch()
    global_config: Path = tmp_path_factory.mktemp("gitconfig") / "config"
    global_config.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    try:
        yield
    finally:
        monkeypatch.undo()
