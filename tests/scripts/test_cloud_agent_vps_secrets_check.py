"""Smoke test for scripts/cloud_agent_vps_secrets_check.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cloud_agent_vps_secrets_check.sh"


def test_secrets_check_ok_when_env_set(monkeypatch) -> None:
    monkeypatch.setenv("VPS", "user@example.test")
    monkeypatch.setenv("VPSPASS", "not-printed")
    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "VPS": "user@example.test", "VPSPASS": "not-printed"},
    )
    assert proc.returncode == 0
    assert "OK" in proc.stdout
    assert "not-printed" not in proc.stdout + proc.stderr


def test_secrets_check_fails_without_env(monkeypatch) -> None:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("VPS", "VPSPASS", "vps", "password")
    }
    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 1
    assert "FAIL" in proc.stderr
