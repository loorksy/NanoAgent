"""SSH auth path helpers (no live VPS required)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "scripts" / "cloud_agent_vps_secrets_check.sh"


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
