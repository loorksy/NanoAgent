"""Composition helpers for the embedded Mokli gateway."""

from __future__ import annotations

from collections.abc import Awaitable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from loguru import logger as default_logger

from mokli.config.loader import get_config_path
from mokli.surface.gateway_endpoint import MokliGatewayEndpoint
from mokli.surface.gateway_tokens import GatewayTokenStore
from mokli.surface.ingress_policy import DEFAULT_MOKLI_INGRESS_POLICY, MokliIngressPolicy
from mokli.surface.media_gateway import MokliMediaGateway
from mokli.surface.session_projection import MokliSessionProjection
from mokli.surface.settings_services import MokliSettingsServices
from mokli.surface.temporary_chats import MokliTemporaryChats
from mokli.surface.transcript import MokliTranscriptRecorder
from mokli.surface.workspaces import MokliWorkspaceController
from mokli.surface.ws_http import GatewayHTTPHandler

if TYPE_CHECKING:
    from mokli.bus.queue import MessageBus
    from mokli.channels.websocket.runtime import WebSocketConfig
    from mokli.cron.service import CronService
    from mokli.session.manager import SessionManager
    from mokli.triggers.local_store import LocalTriggerStore


@dataclass(frozen=True)
class GatewayServices:
    """Explicit dependencies shared by WebSocket transport and HTTP routes."""

    http: GatewayHTTPHandler
    endpoint: MokliGatewayEndpoint
    settings: MokliSettingsServices
    tokens: GatewayTokenStore
    media: MokliMediaGateway
    ingress: MokliIngressPolicy
    transcripts: MokliTranscriptRecorder
    workspaces: MokliWorkspaceController
    temporary_chats: MokliTemporaryChats
    session_projection: MokliSessionProjection
    session_manager: SessionManager | None
    cron_service: CronService | None
    local_trigger_store: LocalTriggerStore | None
    cron_pending_job_ids: Callable[[str], set[str]] | None
    local_trigger_pending_ids: Callable[[str], set[str]] | None


def build_gateway_services(
    *,
    config: WebSocketConfig,
    bus: MessageBus,
    session_manager: SessionManager | None,
    static_dist_path: Path | None,
    workspace_path: Path,
    default_restrict_to_workspace: bool,
    config_path: Path | None = None,
    runtime_model_name: Callable[[], str | None] | None,
    refresh_runtime_config: Callable[[], None] | None = None,
    runtime_surface: str,
    runtime_capabilities_overrides: dict[str, Any] | None,
    disabled_skills: set[str] | None = None,
    cron_service: CronService | None = None,
    local_trigger_store: LocalTriggerStore | None = None,
    cron_pending_job_ids: Callable[[str], set[str]] | None = None,
    local_trigger_pending_ids: Callable[[str], set[str]] | None = None,
    channel_feature_action: Callable[..., Any] | None = None,
    channel_runtime_status: Callable[[], dict[str, Any]] | None = None,
    mcp_runtime_status: Callable[[], Mapping[str, str]] | None = None,
    mcp_reload: Callable[[], Awaitable[dict[str, Any]]] | None = None,
    skill_state_action: Callable[[set[str]], None] | None = None,
    recovery_action: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]] | None = None,
    logger: Any = default_logger,
) -> GatewayServices:
    settings = MokliSettingsServices.create(
        config_path or get_config_path(),
        rename_model_preset=(
            session_manager.rename_model_preset
            if session_manager is not None
            else None
        ),
        refresh_runtime_config=refresh_runtime_config,
    )
    tokens = GatewayTokenStore()
    ingress = DEFAULT_MOKLI_INGRESS_POLICY
    minimum_frame_bytes = ingress.minimum_full_policy_frame_bytes()
    if config.max_message_bytes < minimum_frame_bytes:
        logger.warning(
            "WebSocket maxMessageBytes={} is below the Mokli ingress policy capacity={}; "
            "policy-valid messages may still hit the transport frame guard",
            config.max_message_bytes,
            minimum_frame_bytes,
        )
    media = MokliMediaGateway(
        workspace_path=workspace_path,
        logger=logger,
        attachment_limits=ingress.attachments,
    )
    transcripts = MokliTranscriptRecorder(log=logger)
    workspaces = MokliWorkspaceController(
        session_manager=session_manager,
        default_workspace=workspace_path,
        default_restrict_to_workspace=default_restrict_to_workspace,
    )
    temporary_chats = MokliTemporaryChats(
        bus=bus,
        session_manager=session_manager,
        workspaces=workspaces,
        logger=logger,
    )
    session_projection = MokliSessionProjection(session_manager, log=logger)
    http = GatewayHTTPHandler(
        config=config,
        session_manager=session_manager,
        static_dist_path=static_dist_path,
        runtime_model_name=runtime_model_name,
        runtime_surface=runtime_surface,
        runtime_capabilities_overrides=runtime_capabilities_overrides,
        bus=bus,
        tokens=tokens,
        media=media,
        ingress=ingress,
        workspaces=workspaces,
        settings=settings,
        skills_workspace_path=workspace_path,
        disabled_skills=disabled_skills,
        cron_service=cron_service,
        local_trigger_store=local_trigger_store,
        cron_pending_job_ids=cron_pending_job_ids,
        local_trigger_pending_ids=local_trigger_pending_ids,
        channel_feature_action=channel_feature_action,
        channel_runtime_status=channel_runtime_status,
        mcp_runtime_status=mcp_runtime_status,
        mcp_reload=mcp_reload,
        skill_state_action=skill_state_action,
        recovery_action=recovery_action,
        log=logger,
    )
    endpoint = MokliGatewayEndpoint(config=config, http=http, tokens=tokens)
    return GatewayServices(
        http=http,
        endpoint=endpoint,
        settings=settings,
        tokens=tokens,
        media=media,
        ingress=ingress,
        transcripts=transcripts,
        workspaces=workspaces,
        temporary_chats=temporary_chats,
        session_projection=session_projection,
        session_manager=session_manager,
        cron_service=cron_service,
        local_trigger_store=local_trigger_store,
        cron_pending_job_ids=cron_pending_job_ids,
        local_trigger_pending_ids=local_trigger_pending_ids,
    )
