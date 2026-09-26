"""Loader for team specialist prompts stored under ``nanobot/agent/prompt/team_roles``."""

from __future__ import annotations

from nanobot.agent.prompt.composer import (
    DEFAULT_PRODUCT_NAME,
    DEFAULT_REPLY_LANGUAGE,
    compose_team_role_prompt,
    team_role_names,
)

ROLE_REFERENCE_PREFIX = "role:"
DEFAULT_ROLE_FILE = "lead"

# Ordered: the first keyword found in the normalised role label wins.
_ROLE_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("macro", "macro"),
    ("structure", "structure"),
    ("liquidity", "liquidity"),
    ("scenario", "scenario"),
    ("event", "event"),
    ("news", "news"),
    ("war", "news"),
    ("mtf", "mtf_synthesizer"),
    ("synth", "mtf_synthesizer"),
    ("risk", "risk"),
    ("officer", "risk"),
    ("bull", "bull"),
    ("bear", "bear"),
    ("lead", "lead"),
    ("committee", "lead"),
    ("h1", "timeframe"),
    ("h4", "timeframe"),
    ("d1", "timeframe"),
    ("timeframe", "timeframe"),
)


def role_file_for(role: str) -> str:
    """Map a preset role label (``"Bull Advocate"``) to a ``team_roles`` file stem."""
    key = (role or "").strip().lower()
    for keyword, file_stem in _ROLE_KEYWORDS:
        if keyword in key:
            return file_stem
    return DEFAULT_ROLE_FILE


def resolve_role_file(role: str, system_prompt: str = "") -> str:
    """Honour an explicit ``role:<file>`` reference from a preset before falling back."""
    reference = (system_prompt or "").strip()
    if reference.startswith(ROLE_REFERENCE_PREFIX):
        stem = reference[len(ROLE_REFERENCE_PREFIX):].strip()
        if stem in team_role_names():
            return stem
    return role_file_for(role)


def list_role_files() -> list[str]:
    return team_role_names()


def role_system_prompt(
    role: str,
    *,
    system_prompt: str = "",
    product_name: str = DEFAULT_PRODUCT_NAME,
    reply_language: str = DEFAULT_REPLY_LANGUAGE,
) -> str:
    """Full system prompt for one team role (shared preamble plus the role file)."""
    return compose_team_role_prompt(
        resolve_role_file(role, system_prompt),
        product_name=product_name,
        reply_language=reply_language,
        role_label=(role or "").strip() or DEFAULT_ROLE_FILE.title(),
    )
