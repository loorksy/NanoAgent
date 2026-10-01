"""SSH auth path helpers (no live VPS required)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "scripts" / "cloud_agent_vps_secrets_check.sh"
VPS_SSH = ROOT / "scripts" / "vps_ssh.sh"


def test_vps_ssh_defaults_hostinger_when_no_vps_env() -> None:
    proc = subprocess.run(
        [
            "bash",
            "-c",
            f"unset MOKLI_SSH_HOST VPS VPSPASS; source {VPS_SSH}; printf '%s' \"${{MOKLI_SSH_HOST:-}}\"",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout == "hostinger-vps"


def test_vps_ssh_script_runs_remote_command_when_key_works() -> None:
    proc = subprocess.run(
        [str(VPS_SSH), "echo", "vps_ssh_cli_ok"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if proc.returncode == 0:
        assert "vps_ssh_cli_ok" in proc.stdout
    else:
        # 5 = SSH "Permission denied" under parallel aggregate runs; 255 = unreachable.
        assert proc.returncode in (1, 5, 255)
        if proc.returncode == 1:
            assert "MOKLI_SSH_HOST" in proc.stderr or "VPS" in proc.stderr


def test_vps_ssh_leaves_host_empty_when_vps_password_target_set() -> None:
    proc = subprocess.run(
        [
            "bash",
            "-c",
            f"unset MOKLI_SSH_HOST; export VPS=user@example.com; source {VPS_SSH}; "
            "if [[ -n \"${MOKLI_SSH_HOST:-}\" ]]; then echo set; else echo unset; fi",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.strip() == "unset"


def test_secrets_check_accepts_mokli_ssh_host_when_key_works(monkeypatch) -> None:
    monkeypatch.setenv("MOKLI_SSH_HOST", "hostinger-vps")
    env = {k: v for k, v in os.environ.items() if k not in ("VPS", "VPSPASS", "vps", "password")}
    env["MOKLI_SSH_HOST"] = "hostinger-vps"
    proc = subprocess.run(
        ["bash", str(CHECK)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=30,
    )
    if proc.returncode == 0:
        assert "MOKLI_SSH_HOST" in proc.stdout
    else:
        # CI / sandboxes without SSH config: must not claim password OK.
        assert "VPS deploy credentials" in proc.stderr or "MOKLI_SSH_HOST" in proc.stderr
