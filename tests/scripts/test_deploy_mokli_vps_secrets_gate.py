"""Deploy script must refuse SSH when VPS credentials are absent."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "scripts" / "deploy-mokli-vps.sh"


def test_deploy_exits_when_vps_credentials_missing() -> None:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("VPS", "VPSPASS", "vps", "password")
    }
    proc = subprocess.run(
        ["bash", str(DEPLOY)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=30,
    )
    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert "VPS deploy credentials" in combined or "cloud_agent_vps_secrets_check" in combined
