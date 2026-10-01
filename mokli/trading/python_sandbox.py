"""Run reviewed Python and return text. No broker credentials and no trade calls.

Isolation, in order:

1. ``review_python`` rejects the source.
2. The child process receives a scrubbed environment (no ``MT5_*`` and no
   inherited secrets).
3. When ``bwrap`` can start, the child runs with ``--unshare-all`` (no network
   namespace, no host mounts except the interpreter and this bootstrap).
4. Otherwise a fresh Python process applies the same resource limits and
   socket block. The result names the isolation that actually ran.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from mokli.trading.code_policy import review_python

BOOTSTRAP = Path(__file__).with_name("python_sandbox_bootstrap.py")
DEFAULT_TIMEOUT_S = 5
MAX_TIMEOUT_S = 15
MEMORY_BYTES = 512 * 1024 * 1024
MAX_OUTPUT_CHARS = 16_000

_SCRUBBED_ENV = {
    "PATH": "/usr/bin:/bin",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONNOUSERSITE": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONSAFEPATH": "1",
}


@dataclass(frozen=True)
class SandboxResult:
    exit_code: int
    isolation: str
    stdout: str
    stderr: str
    timed_out: bool = False

    def render(self) -> str:
        status = "timeout" if self.timed_out else f"exit {self.exit_code}"
        return (
            f"isolation: {self.isolation}\n"
            f"status: {status}\n"
            f"stdout:\n{_clip(self.stdout)}\n"
            f"stderr:\n{_clip(self.stderr)}"
        )


def scrubbed_env() -> dict[str, str]:
    """Environment passed to the child. Never copies the parent environment."""
    return dict(_SCRUBBED_ENV)


def run_python_sandbox(source: str, *, timeout_s: int = DEFAULT_TIMEOUT_S) -> SandboxResult:
    """Review *source*, run it, and return captured text."""
    review_python(source)
    timeout = min(MAX_TIMEOUT_S, max(1, int(timeout_s)))
    with tempfile.TemporaryDirectory(prefix="mokli-py-") as scratch:
        program = Path(scratch) / "program.py"
        program.write_text(source, encoding="utf-8")
        if shutil.which("bwrap"):
            launched = _spawn(
                _bwrap_command(program, timeout),
                isolation="bwrap --unshare-all",
                timeout_s=timeout,
                cwd=scratch,
            )
            if not _bwrap_failed_to_launch(launched):
                return launched
        return _spawn(
            _python_command(program, timeout),
            isolation="subprocess",
            timeout_s=timeout,
            cwd=scratch,
        )


def _python_command(program: Path, timeout_s: int) -> list[str]:
    return [
        sys.executable,
        "-I",
        str(BOOTSTRAP),
        str(program),
        str(MEMORY_BYTES),
        str(timeout_s),
    ]


def _bwrap_command(program: Path, timeout_s: int) -> list[str]:
    bwrap = shutil.which("bwrap") or "bwrap"
    command = [
        bwrap,
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind-try", "/lib", "/lib",
        "--ro-bind-try", "/lib64", "/lib64",
        "--ro-bind-try", "/bin", "/bin",
        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",
        "--ro-bind", str(BOOTSTRAP), "/tmp/bootstrap.py",
        "--ro-bind", str(program), "/tmp/program.py",
        "--chdir", "/tmp",
        "--clearenv",
    ]
    for key, value in _SCRUBBED_ENV.items():
        command.extend(["--setenv", key, value])
    command.extend(
        [
            "--",
            sys.executable,
            "-I",
            "/tmp/bootstrap.py",
            "/tmp/program.py",
            str(MEMORY_BYTES),
            str(timeout_s),
        ]
    )
    return command


def _spawn(command: list[str], *, isolation: str, timeout_s: int, cwd: str) -> SandboxResult:
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        env=scrubbed_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_s + 1)
    except subprocess.TimeoutExpired:
        _kill(proc)
        stdout, stderr = proc.communicate()
        return SandboxResult(
            exit_code=124,
            isolation=isolation,
            stdout=stdout or "",
            stderr=(stderr or "") + "\nexecution timed out",
            timed_out=True,
        )
    code = int(proc.returncode or 0)
    err = stderr or ""
    if code < 0:
        err = f"{err}\nprocess stopped by signal {-code}".strip()
    elif code > 128:
        err = f"{err}\nprocess stopped by signal {code - 128}".strip()
    return SandboxResult(
        exit_code=code,
        isolation=isolation,
        stdout=stdout or "",
        stderr=err,
    )


def _bwrap_failed_to_launch(result: SandboxResult) -> bool:
    """True when bubblewrap itself rejected the sandbox, before user code ran."""
    if result.timed_out or result.exit_code == 0 or result.stdout.strip():
        return False
    text = result.stderr.lower()
    return "bwrap" in text or "unshare" in text or "setting up uid map" in text


def _kill(proc: subprocess.Popen[str]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        proc.kill()


def _clip(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n…[output truncated]"
