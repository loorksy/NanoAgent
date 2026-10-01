"""Policy gate and isolated Python runner. No broker and no network."""

from __future__ import annotations

import os

import pytest

from mokli.trading.code_policy import CodePolicyError, review_python
from mokli.trading.policy_guard import PolicyViolation, validate_tool_call
from mokli.trading.python_sandbox import run_python_sandbox, scrubbed_env


def test_review_allows_a_calculation() -> None:
    review_python("import math\nprint(math.sqrt(4))\n")


@pytest.mark.parametrize(
    "source",
    [
        "import os",
        "import socket",
        "import mt5",
        "print(().__class__)",
        "open('/etc/passwd')",
        "import MetaTrader5",
        "x = 'MT5_PASSWORD'",
    ],
)
def test_review_blocks_host_and_broker_access(source: str) -> None:
    with pytest.raises(CodePolicyError):
        review_python(source)


def test_guard_rejects_before_execution() -> None:
    with pytest.raises(PolicyViolation):
        validate_tool_call("run_python", {"code": "import socket"})


def test_scrubbed_env_drops_parent_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MT5_PASSWORD", "super-secret")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    env = scrubbed_env()
    assert "MT5_PASSWORD" not in env
    assert "super-secret" not in env.values()
    assert os.environ["MT5_PASSWORD"] == "super-secret"


def test_sandbox_returns_stdout_only() -> None:
    result = run_python_sandbox("import math\nprint(int(math.sqrt(9)))\n", timeout_s=5)
    assert result.exit_code == 0
    assert result.stdout.strip() == "3"
    assert result.isolation in {"bwrap --unshare-all", "subprocess"}
    assert "MT5_" not in result.stdout


def test_sandbox_stops_a_busy_loop() -> None:
    result = run_python_sandbox("while True:\n    pass\n", timeout_s=1)
    assert result.exit_code != 0
    stopped = result.timed_out or result.exit_code < 0 or result.exit_code > 128
    assert stopped
