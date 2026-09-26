from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nanobot.agent.context import ContextBuilder
from nanobot.agent.tools.context import RequestContext, request_context
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.spawn import SpawnTool
from nanobot.security.workspace_access import (
    WORKSPACE_SCOPE_METADATA_KEY,
    WorkspaceScopeError,
    WorkspaceScopeResolver,
    bind_workspace_scope,
    default_workspace_scope,
    reset_workspace_scope,
    validate_workspace_scope_payload,
    workspace_scope_from_metadata,
)

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02"
    b"\x00\x00\x00\x0bIDATx\xdacd\xfc\xff\x1f\x00\x03\x03"
    b"\x02\x00\xef\xbf\xa7\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_workspace_scope_defaults_match_legacy_config(tmp_path: Path) -> None:
    unrestricted = default_workspace_scope(tmp_path, restrict_to_workspace=False)
    restricted = default_workspace_scope(tmp_path, restrict_to_workspace=True)

    assert unrestricted.project_path == tmp_path.resolve()
    assert unrestricted.access_mode == "full"
    assert unrestricted.restrict_to_workspace is False
    assert restricted.access_mode == "restricted"
    assert restricted.restrict_to_workspace is True


def test_workspace_scope_rejects_invalid_project_path(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceScopeError, match="absolute"):
        validate_workspace_scope_payload(
            {"project_path": "relative/project", "access_mode": "restricted"},
            default_workspace=tmp_path,
            default_restrict_to_workspace=False,
        )

    with pytest.raises(WorkspaceScopeError, match="existing directory"):
        validate_workspace_scope_payload(
            {"project_path": str(tmp_path / "missing"), "access_mode": "restricted"},
            default_workspace=tmp_path,
            default_restrict_to_workspace=False,
        )


def test_workspace_scope_accepts_home_relative_project_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    project = home / "Desktop" / "Photos"
    project.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))

    scope = validate_workspace_scope_payload(
        {"project_path": "~/Desktop/Photos", "access_mode": "restricted"},
        default_workspace=tmp_path,
        default_restrict_to_workspace=False,
    )

    assert scope.project_path == project.resolve()
    assert scope.metadata()["project_path"] == str(project.resolve())


@pytest.mark.parametrize("access_mode", ["restricted", "full"])
def test_selected_websocket_project_is_visible_to_the_model(
    tmp_path: Path,
    access_mode: str,
) -> None:
    agent_home = tmp_path / "agent-home"
    project = tmp_path / "project"
    agent_home.mkdir()
    project.mkdir()
    resolver = WorkspaceScopeResolver(agent_home, default_restrict_to_workspace=False)

    scope = resolver.for_turn(
        channel="websocket",
        message_metadata={
            WORKSPACE_SCOPE_METADATA_KEY: {
                "project_path": str(project),
                "access_mode": access_mode,
            }
        },
        session_metadata=None,
    )
    prompt = ContextBuilder(agent_home).build_system_prompt(workspace=scope.project_path)

    assert prompt.index("# Tool contracts") < prompt.index("# Current Project")
    assert f"Working directory: {project.resolve()}" in prompt
    assert "Use it as the default root for project files" in prompt


def test_workspace_scope_metadata_falls_back_for_stale_session(tmp_path: Path) -> None:
    scope = workspace_scope_from_metadata(
        {
            WORKSPACE_SCOPE_METADATA_KEY: {
                "project_path": str(tmp_path / "missing"),
                "access_mode": "restricted",
            }
        },
        default_workspace=tmp_path,
        default_restrict_to_workspace=False,
    )

    assert scope.project_path == tmp_path.resolve()
    assert scope.access_mode == "full"


def test_message_media_scope_restricted_blocks_outside_and_full_allows(tmp_path: Path) -> None:
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    media = outside / "shot.png"
    media.write_bytes(PNG_BYTES)
    tool = MessageTool(workspace=tmp_path, restrict_to_workspace=True)

    restricted = validate_workspace_scope_payload(
        {"project_path": str(project), "access_mode": "restricted"},
        default_workspace=tmp_path,
        default_restrict_to_workspace=False,
    )
    token = bind_workspace_scope(restricted)
    try:
        with pytest.raises(PermissionError):
            tool._resolve_media([str(media)])
    finally:
        reset_workspace_scope(token)

    full = validate_workspace_scope_payload(
        {"project_path": str(project), "access_mode": "full"},
        default_workspace=tmp_path,
        default_restrict_to_workspace=True,
    )
    token = bind_workspace_scope(full)
    try:
        assert tool._resolve_media([str(media)]) == [str(media)]
    finally:
        reset_workspace_scope(token)


@pytest.mark.asyncio
async def test_spawn_tool_forwards_current_workspace_scope(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    scope = validate_workspace_scope_payload(
        {"project_path": str(project), "access_mode": "restricted"},
        default_workspace=tmp_path,
        default_restrict_to_workspace=False,
    )

    class Manager:
        max_concurrent_subagents = 4

        def __init__(self) -> None:
            self.seen = None

        def get_running_count(self) -> int:
            return 0

        async def spawn(self, **kwargs):
            self.seen = kwargs
            return "spawned"

    manager = Manager()
    tool = SpawnTool(manager)  # type: ignore[arg-type]
    token = bind_workspace_scope(scope)
    try:
        with request_context(RequestContext(
            channel="test",
            chat_id="chat",
            runtime=MagicMock(),
        )):
            result = await tool.execute(task="inspect")
    finally:
        reset_workspace_scope(token)

    assert result == "spawned"
    assert manager.seen["workspace_scope"] == scope
