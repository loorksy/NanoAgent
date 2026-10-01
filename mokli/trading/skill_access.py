"""Allowlist for reading skill and profile files. No writes, no secrets."""

from __future__ import annotations

from pathlib import Path

MAX_READ_CHARS = 32_000
PROFILE_FILES = frozenset(
    {
        "SOUL.md",
        "USER.md",
        "AGENTS.md",
        "HEARTBEAT.md",
        "memory/MEMORY.md",
        "memory/history.jsonl",
    }
)
_SECRET_NAMES = frozenset(
    {
        ".env",
        ".env.local",
        "config.json",
        "credentials.json",
        "secrets.json",
    }
)
_SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
_SECRET_TOKENS = ("password", "secret", "credential", "token")


class SkillPathError(ValueError):
    """The requested path is outside the readable set."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def builtin_skills_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "skills"


def resolve_readable(workspace: Path, raw: str, *, builtin: Path | None = None) -> Path:
    """Return a resolved file the model may read, or raise ``SkillPathError``."""
    root = workspace.expanduser().resolve()
    skills = builtin_skills_dir() if builtin is None else builtin.resolve()
    text = (raw or "").strip()
    if not text:
        raise SkillPathError("path is empty")
    candidate = Path(text)
    options = [candidate] if candidate.is_absolute() else [root / candidate, skills / candidate]
    for option in options:
        try:
            resolved = option.resolve()
        except OSError as exc:
            raise SkillPathError("path is not readable") from exc
        if _is_secret(resolved):
            raise SkillPathError("path is not readable")
        if not resolved.is_file():
            continue
        if _under(resolved, skills) or _under(resolved, root / "skills"):
            if resolved.suffix.lower() not in {".md", ".txt"}:
                raise SkillPathError("only markdown skill files are readable")
            return resolved
        try:
            relative = resolved.relative_to(root).as_posix()
        except ValueError:
            continue
        if relative in PROFILE_FILES:
            return resolved
    raise SkillPathError("path is outside skill and profile files")


def read_text(path: Path, *, offset: int = 1, limit: int = 400) -> str:
    """Return a line window from an already-resolved file."""
    start = max(1, int(offset))
    count = max(1, min(400, int(limit)))
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    window = lines[start - 1 : start - 1 + count]
    body = "\n".join(window)
    if len(body) > MAX_READ_CHARS:
        body = body[:MAX_READ_CHARS] + "\n…[truncated]"
    return body


def grep_skills(
    workspace: Path,
    pattern: str,
    *,
    path: str = "",
    glob: str = "*.md",
    builtin: Path | None = None,
    limit: int = 40,
) -> str:
    """Search skill markdown. ``pattern`` is a literal substring, not a regex."""
    needle = (pattern or "").strip()
    if not needle:
        raise SkillPathError("pattern is empty")
    if len(needle) > 200:
        raise SkillPathError("pattern is too long")
    files = _search_files(workspace, path=path, glob=glob or "*.md", builtin=builtin)
    hits: list[str] = []
    cap = max(1, min(40, int(limit)))
    for file in files:
        try:
            lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, start=1):
            if needle not in line:
                continue
            snippet = line.strip()
            if len(snippet) > 200:
                snippet = snippet[:200] + "…"
            hits.append(f"{file}:{number}: {snippet}")
            if len(hits) >= cap:
                return "\n".join(hits)
    return "\n".join(hits)


def _search_files(workspace: Path, *, path: str, glob: str, builtin: Path | None) -> list[Path]:
    root = workspace.expanduser().resolve()
    skills = builtin_skills_dir() if builtin is None else builtin.resolve()
    roots = [skills, root / "skills"]
    if path.strip():
        target = _resolve_search_root(root, skills, path)
        if target.is_file():
            return [target]
        roots = [target]
    found: list[Path] = []
    pattern = glob if any(ch in glob for ch in "*?[]") else glob
    for base in roots:
        if not base.exists():
            continue
        if base.is_file():
            found.append(base)
            continue
        found.extend(
            item for item in base.rglob(pattern) if item.is_file() and not _is_secret(item)
        )
    return found


def _resolve_search_root(workspace: Path, skills: Path, raw: str) -> Path:
    candidate = Path(raw.strip())
    if candidate.is_absolute():
        options = [candidate]
    else:
        options = [workspace / candidate, skills / candidate]
    for option in options:
        resolved = option.resolve()
        if _is_secret(resolved):
            raise SkillPathError("path is not readable")
        allowed = _under(resolved, skills) or _under(resolved, workspace / "skills")
        if allowed and (resolved.is_dir() or resolved.is_file()):
            return resolved
    raise SkillPathError("path is outside skill files")


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _is_secret(path: Path) -> bool:
    name = path.name.lower()
    if name in _SECRET_NAMES or name.startswith(".env"):
        return True
    if name.endswith(_SECRET_SUFFIXES):
        return True
    return any(token in name for token in _SECRET_TOKENS)
