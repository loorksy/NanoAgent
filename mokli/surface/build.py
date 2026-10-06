"""Helpers for keeping the bundled Mokli build in sync with source checkouts."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

BuildMode = Literal["auto", "prompt", "warn", "skip"]

_SOURCE_TOP_LEVEL_FILES = (
    "index.html",
    "package.json",
    "bun.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "vite.config.ts",
    "vite.config.js",
    "tailwind.config.ts",
    "tailwind.config.js",
    "postcss.config.ts",
    "postcss.config.js",
    "tsconfig.json",
    "tsconfig.build.json",
    "components.json",
)
_SOURCE_DIRS = ("src", "public")


class MokliBuildError(RuntimeError):
    """Raised when the local Mokli bundle cannot be built."""


@dataclass(frozen=True)
class MokliBundleStatus:
    """Freshness status for a source checkout's bundled Mokli assets."""

    source_dir: Path
    dist_dir: Path
    index_html: Path
    source_available: bool
    dist_available: bool
    stale: bool
    reason: str
    newest_source: Path | None = None
    newest_source_mtime_ns: int | None = None
    dist_mtime_ns: int | None = None

    @property
    def needs_build(self) -> bool:
        return self.source_available and self.stale


def default_project_root() -> Path:
    """Return the repository root when running from a source checkout."""
    return Path(__file__).resolve().parents[2]


def default_mokli_source_dir(project_root: Path | None = None) -> Path:
    """Return the conventional frontend source directory for a checkout."""
    root = project_root or default_project_root()
    return root / "mokli"


def default_mokli_dist_dir(project_root: Path | None = None) -> Path:
    """Return the bundled Mokli dist directory for the installed package."""
    try:
        import mokli.web as web_pkg  # type: ignore[import-not-found]
    except ImportError:
        root = project_root or default_project_root()
        return root / "mokli" / "web" / "dist"
    return Path(web_pkg.__file__).resolve().parent / "dist"


def iter_mokli_source_files(source_dir: Path) -> list[Path]:
    """Return Mokli source files that should make the production bundle stale."""
    files: list[Path] = []
    for name in _SOURCE_TOP_LEVEL_FILES:
        candidate = source_dir / name
        if candidate.is_file():
            files.append(candidate)
    for dirname in _SOURCE_DIRS:
        root = source_dir / dirname
        if not root.is_dir():
            continue
        files.extend(path for path in root.rglob("*") if path.is_file())
    shared_root = source_dir.parent / "packages" / "client-events"
    if shared_root.is_dir():
        files.extend(path for path in shared_root.rglob("*") if path.is_file())
    channel_root = source_dir.parent / "mokli" / "channels"
    if channel_root.is_dir():
        for channel_mokli in channel_root.glob("*/mokli"):
            files.extend(path for path in channel_mokli.rglob("*") if path.is_file())
    return files


def inspect_mokli_bundle(
    *,
    source_dir: Path | None = None,
    dist_dir: Path | None = None,
) -> MokliBundleStatus:
    """Inspect whether a checkout's Mokli source is newer than the bundled dist."""
    resolved_source = source_dir or default_mokli_source_dir()
    resolved_dist = dist_dir or default_mokli_dist_dir()
    index_html = resolved_dist / "index.html"

    if not (resolved_source / "package.json").is_file():
        return MokliBundleStatus(
            source_dir=resolved_source,
            dist_dir=resolved_dist,
            index_html=index_html,
            source_available=False,
            dist_available=index_html.is_file(),
            stale=False,
            reason="no_source",
        )

    if not index_html.is_file():
        return MokliBundleStatus(
            source_dir=resolved_source,
            dist_dir=resolved_dist,
            index_html=index_html,
            source_available=True,
            dist_available=False,
            stale=True,
            reason="missing_dist",
        )

    dist_mtime_ns = index_html.stat().st_mtime_ns
    newest_source: Path | None = None
    newest_source_mtime_ns: int | None = None
    for candidate in iter_mokli_source_files(resolved_source):
        try:
            mtime_ns = candidate.stat().st_mtime_ns
        except OSError:
            continue
        if newest_source_mtime_ns is None or mtime_ns > newest_source_mtime_ns:
            newest_source = candidate
            newest_source_mtime_ns = mtime_ns

    if newest_source_mtime_ns is not None and newest_source_mtime_ns > dist_mtime_ns:
        return MokliBundleStatus(
            source_dir=resolved_source,
            dist_dir=resolved_dist,
            index_html=index_html,
            source_available=True,
            dist_available=True,
            stale=True,
            reason="source_newer",
            newest_source=newest_source,
            newest_source_mtime_ns=newest_source_mtime_ns,
            dist_mtime_ns=dist_mtime_ns,
        )

    return MokliBundleStatus(
        source_dir=resolved_source,
        dist_dir=resolved_dist,
        index_html=index_html,
        source_available=True,
        dist_available=True,
        stale=False,
        reason="fresh",
        newest_source=newest_source,
        newest_source_mtime_ns=newest_source_mtime_ns,
        dist_mtime_ns=dist_mtime_ns,
    )


def describe_mokli_bundle_status(status: MokliBundleStatus) -> str:
    """Return a short user-facing freshness message."""
    if status.reason == "missing_dist":
        return "Bundled Mokli build is missing."
    if status.reason == "source_newer":
        changed = _display_source_path(status)
        return f"Mokli source is newer than the bundled build ({changed})."
    if status.reason == "fresh":
        return "Bundled Mokli build is up to date."
    return "Mokli source tree was not found; using the bundled build."


def build_mokli_bundle(
    *,
    source_dir: Path | None = None,
    dist_dir: Path | None = None,
    runner: str | None = None,
    subprocess_run: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
    output: Callable[[str], None] | None = None,
) -> MokliBundleStatus:
    """Install frontend dependencies and build the Mokli bundle."""
    resolved_source = source_dir or default_mokli_source_dir()
    command_runner = runner or pick_mokli_build_runner()
    if command_runner is None:
        raise MokliBuildError(
            "neither `bun` nor `npm` is available on PATH; install one or run "
            "`cd mokli && bun run build` manually"
        )

    _emit(output, f"Building bundled Mokli with `{command_runner}`...")
    _run_frontend_command(
        [command_runner, "install"],
        cwd=resolved_source,
        subprocess_run=subprocess_run,
    )
    _run_frontend_command(
        [command_runner, "run", "build"],
        cwd=resolved_source,
        subprocess_run=subprocess_run,
    )
    return inspect_mokli_bundle(source_dir=resolved_source, dist_dir=dist_dir)


def ensure_mokli_bundle(
    *,
    mode: BuildMode,
    source_dir: Path | None = None,
    dist_dir: Path | None = None,
    confirm: Callable[[str], bool] | None = None,
    output: Callable[[str], None] | None = None,
    runner: str | None = None,
    environ: Mapping[str, str] | None = None,
    subprocess_run: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> MokliBundleStatus:
    """Ensure or warn about a stale Mokli bundle according to the selected mode."""
    env = environ or os.environ
    status = inspect_mokli_bundle(source_dir=source_dir, dist_dir=dist_dir)
    if not status.needs_build:
        return status

    detail = describe_mokli_bundle_status(status)
    if env.get("MOKLI_SKIP_MOKLI_BUILD") == "1" or mode == "skip":
        _emit(output, f"Warning: {detail} Skipping Mokli build.")
        return status

    if mode == "warn":
        _emit(
            output,
            f"Warning: {detail} Run `cd {status.source_dir} && bun run build` "
            "to refresh it.",
        )
        return status

    if mode == "prompt":
        if confirm is None:
            _emit(output, f"Warning: {detail} No interactive confirmation is available.")
            return status
        message = "Build Mokli now? This runs `cd mokli && bun run build`."
        if not confirm(message):
            _emit(output, "Continuing with the existing bundled Mokli build.")
            return status

    try:
        return build_mokli_bundle(
            source_dir=status.source_dir,
            dist_dir=status.dist_dir,
            runner=runner,
            subprocess_run=subprocess_run,
            output=output,
        )
    except MokliBuildError as exc:
        raise MokliBuildError(f"{detail} {exc}") from exc


def pick_mokli_build_runner() -> str | None:
    """Pick the frontend package manager used to build the Mokli."""
    for candidate in ("bun", "npm"):
        if executable := shutil.which(candidate):
            return executable
    return None


def _run_frontend_command(
    command: list[str],
    *,
    cwd: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[Any]],
) -> None:
    try:
        subprocess_run(command, cwd=cwd, check=True)
    except subprocess.CalledProcessError as exc:
        raise MokliBuildError(
            f"command failed ({exc.returncode}): {' '.join(command)}"
        ) from exc
    except OSError as exc:
        raise MokliBuildError(f"command failed: {' '.join(command)} ({exc})") from exc


def _display_source_path(status: MokliBundleStatus) -> str:
    if status.newest_source is None:
        return "source files changed"
    with suppress(ValueError):
        return str(status.newest_source.relative_to(status.source_dir))
    return str(status.newest_source)


def _emit(output: Callable[[str], None] | None, message: str) -> None:
    if output is not None:
        output(message)
