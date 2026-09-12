<!-- المرحلة 2 من Master Project Documentation — Core Files الجزء أ. لا يحتوي أسراراً من .env. -->

# Master Project Documentation — المرحلة 2: الملفات الأساسية (Core Files) — الجزء أ

- **نطاق هذه المرحلة:** أول 85 ملفاً من قائمة Core Files المرتبة في المرحلة 1 (المجموع 170 بعد توسيع المجلدات إلى ملفات).
- **نقطة القطع:** آخر ملف في الجزء أ هو `nanobot/trading/agents/market_data.py`.
- **أول ملف في الجزء ب (المرحلة 3):** `nanobot/trading/agents/multi_timeframe.py`.
- **لم يُقرأ:** `.env`. أسماء متغيرات OANDA تظهر فقط لأنها تُقرأ في `nanobot/trading/config.py` عبر `os.environ.get`.
- **قاعدة USED_BY:** يُذكر كل مستورد إنتاجي تحت `nanobot/` و`scripts/` بالاسم. الاختبارات تُذكر بالعدد + المسارات إذا كان العدد ≤ 12، وإلا يُذكر العدد ومجلدات الاختبار.
- **شجرة المرحلة 1:** اكتملت كتابتها في `docs/master-project/01-architecture.md` القسم 8 (4271 سطراً).

### مفتاح أعمدة الجدول

| العمود | المعنى |
|---|---|
| المسار | مسار الملف من جذر المستودع |
| الوظيفة | ماذا يفعل الملف في المنتج |
| الكلاسات / الدوال الرئيسية | الرموز ذات المستوى الأعلى |
| Imports | الاستيرادات المباشرة (بدون اختبارات TYPE_CHECKING إن أمكن) |
| يُستخدم بواسطة | من يستورد هذا الملف |

---

## 1. تشغيل المنصة والتعبئة (001–043)

| # | المسار | الوظيفة | الكلاسات / الدوال الرئيسية | Imports | يُستخدم بواسطة |
|---:|---|---|---|---|---|
| 001 | `pyproject.toml` | بيان الحزمة `nanobot-ai` 0.3.0: التبعيات، extras، مدخل `nanobot` و`nanobot-desktop-tui`، إعداد ruff/pytest/hatch | لا ينطبق (TOML) | لا ينطبق | Hatch، pip، أدوات الجودة، `nanobot/__init__.py` يقرأ الإصدار |
| 002 | `hatch_build.py` | خطاف Hatch يبني WebUI (Vite) ويضعها في `nanobot/web/dist` عند التعبئة | `WebUIBuildHook.initialize`؛ `_load_webui_build_module`؛ `_PROJECT_ROOT` | `os`, `sys`, `pathlib.Path`, `types.ModuleType`, `hatchling.builders.hooks.plugin.interface.BuildHookInterface`, `nanobot.webui.build` | يستدعيه Hatch وقت البناء فقط (لا استيراد إنتاجي آخر) |
| 003 | `nanobot/__init__.py` | تصدير واجهة الحزمة وإصدارها الكسول (`__getattr__`) | `_read_pyproject_version`, `_resolve_version`, `_LAZY_EXPORTS`, `__getattr__` | `tomllib`, `importlib.metadata`, `pathlib.Path`؛ تصدير كسول لـ `Nanobot` و`StreamEvent` و`RequestContext` | 618 مستورداً عبر `import nanobot` / `from nanobot import` (كل الاختبارات تقريباً + CLI + SDK) |
| 004 | `nanobot/__main__.py` | مدخل `python -m nanobot` | يستدعي `main` فقط | `from nanobot.cli.entry import main` | مشغّل الوحدة القياسي |
| 005 | `nanobot/cli/entry.py` | موزّع خفيف: بدون أمر → agent/TUI؛ وإلا تطبيق Typer الكامل | `_ROOT_OPTIONS`, `_agent_invocation_args`, `_native_tui_candidate`, `_configure_windows_console`, `_run_agent`, `main` | `os`, `sys`, `nanobot.cli.process_identity`, ثم كسولاً `typer`, `nanobot.cli.agent`, `nanobot.cli.commands`, `nanobot.cli.desktop_target` | `nanobot/__main__.py`, `nanobot/cli/commands.py`, `tests/cli/test_entry.py` |
| 006 | `nanobot/cli/commands.py` | تطبيق Typer الكامل: onboard, trigger, serve, webui, gateway, agent, sessions, channels, plugins, status, provider | `_DesktopAwareGroup.parse_args`؛ `version_callback`, `main`, `onboard`, `trigger`, `serve`, `sessions_restore_workspace`, `channels_status`, `channels_login`, `plugins_list`, `plugins_enable`, `plugins_disable`, `status` | `typer`, `loguru`, `rich`, `nanobot.agent.loop.AgentLoop`, `nanobot.cli.gateway.create_gateway_app`, `nanobot.cli.gateway_runtime._run_gateway`, `nanobot.cli.agent`, `nanobot.cli.webui`, `nanobot.config.*`, `nanobot.security.network` | `nanobot/cli/entry.py`؛ اختبارات `tests/cli/test_commands.py`, `tests/cli/test_agent_interactive.py`, `tests/cli/test_config_diagnostics.py`, `tests/cli/test_process_identity.py`, `tests/channels/test_channel_plugins.py`, `tests/config/test_config_migration.py`, `tests/config/test_timezone.py`, `tests/cli/test_safe_file_history.py`, `tests/providers/test_sanitize_surrogates.py` |
| 007 | `nanobot/cli/gateway.py` | أوامر `nanobot gateway` (foreground/background/service) | `create_gateway_app`, `_resolved_config_selector` | `typer`, `nanobot.gateway.*`, `nanobot.gateway.service.*`, `nanobot.webui.build.BuildMode` | `nanobot/cli/commands.py`, `tests/cli/test_gateway_commands.py` |
| 008 | `nanobot/cli/gateway_runtime.py` | دورة حياة البوابة الأمامية: AgentLoop + MCP + القنوات + WebUI + health + heartbeat | `_MCPReadinessHook`؛ `_run_gateway`, `_gateway_readiness_payload`, `_close_gateway_runtime`, `_install_gateway_shutdown_handlers`, `_print_gateway_health_endpoint` | `AgentLoop`, `MCPProvider`, `ToolRegistry`, `MessageBus`, `ChannelManager`, `watch_config_file`, `CronService`, `nanobot.trading.cron` (تسجيل وظائف الذهب) | `nanobot/cli/commands.py`؛ `tests/cli/test_gateway_runtime.py`, `tests/cli/test_commands.py` |
| 009 | `nanobot/cli/agent.py` | أمر الوكيل التفاعلي / رسالة واحدة؛ يطلق TUI ما لم يُطلب classic | `agent`, `_classic_dependency`, `_CLASSIC_DEPENDENCIES` | `AgentLoop` عبر المسار الكلاسيكي، `MessageBus`, `MCPProvider`, `launch_tui`, `make_provider` | `nanobot/cli/entry.py`, `nanobot/cli/commands.py`, `tests/cli/test_tui_launcher.py` |
| 010 | `nanobot/cli/webui.py` | أمر `nanobot webui`: يجهّز الحزمة ويربط/يفتح المتصفح | `webui`, `_wait_with_existing_foreground_gateway` | `nanobot.cli.webui_support.*`, `GatewayRuntime`, `WebUIDevServer` | `nanobot/cli/commands.py` |
| 011 | `nanobot/cli/desktop_tui.py` | مدخل `nanobot-desktop-tui`: بروتوكول أنبوب لسطح المكتب | `PROTOCOL_VERSION`, `resolve_request`, `launch_desktop_tui`, `main` | `nanobot.cli.desktop_target`, `nanobot.cli.tui_launcher` | `nanobot/cli/desktop_target.py`؛ console script في `pyproject.toml` |
| 012 | `nanobot/cli/runtime_config.py` | تحميل إعداد التشغيل وتشخيص الأخطاء المشتركة بين أوامر CLI | `_load_runtime_config`, `_load_inspection_config`, `_load_config_for_cli`, `_model_display`, `_print_config_error`, `_migrate_cron_store`, `_provider_setup_error` | `nanobot.config.loader`, `nanobot.config.schema.Config`, `nanobot.config.errors`, `nanobot.providers.factory.validate_provider_setup` | `nanobot/cli/webui.py`, `gateway_runtime.py`, `tui_launcher.py`, `commands.py`, `agent.py`, `webui_support.py`؛ `tests/cli/test_commands.py` |
| 013 | `nanobot/gateway/__init__.py` | إعادة تصدير أنواع البوابة الخلفية | يعيد: `GatewayRuntime`, `GatewayInstance`, `GatewayStatus`, `GatewayClientLease`, `build_gateway_command` | `nanobot.gateway.runtime` | `nanobot/gateway/service.py`, `nanobot/cli/webui.py`, `gateway_runtime.py`, `gateway.py`, `tui_launcher.py`, `webui_support.py`؛ 6 اختبارات gateway/cli |
| 014 | `nanobot/gateway/runtime.py` | تشغيل عملية gateway في الخلفية: قفل، health، restart، lease للعملاء | `GatewayRuntime`, `GatewayInstance`, `GatewayClientLease`, `GatewayAlreadyRunningError`, `GatewayRuntimePaths`, `GatewayStatus`, `build_gateway_command`, `monitor_gateway_clients` | `nanobot.process_runtime.ManagedProcessRuntime`, `nanobot.config.paths.get_data_dir`, `filelock` | `nanobot/gateway/__init__.py`, `nanobot/cli/gateway_runtime.py`, `nanobot/cli/webui_support.py`, `tests/gateway/test_runtime.py` |
| 015 | `nanobot/gateway/service.py` | تثبيت خدمة نظام (systemd / launchd) للبوابة | `GatewayServiceInstaller`, `GatewayServiceOptions`, `GatewayServiceResult`؛ `_install_systemd`, `_install_launchd` | `nanobot.gateway.build_gateway_command` | `nanobot/cli/gateway.py`؛ `tests/gateway/test_gateway_service.py`, `tests/cli/test_gateway_commands.py` |
| 016 | `nanobot/config/__init__.py` | واجهة حزمة الإعداد | يعيد `Config`, `load_config`, `get_config_path`, دوال المسارات، أخطاء التحميل | `nanobot.config.errors`, `loader`, `paths`, `schema` | 189 مستورداً (`from nanobot.config import` شائع في الاختبارات وWebUI) |
| 017 | `nanobot/config/paths.py` | مسارات التشغيل: data, logs, media, cron, workspace, sessions | `get_data_dir`, `get_workspace_path`, `get_cron_dir`, `get_logs_dir`, `get_media_dir`, `get_webui_dir`, `get_cli_history_path`, `get_legacy_sessions_dir`, `is_default_workspace` | `nanobot.utils.helpers.ensure_dir`, `nanobot.config.loader.get_config_path` | إنتاج: `nanobot/trading/recommendations/store.py`, `runtime_state.py`, `paper.py`, `memory/decisions.py`, `channels/telegram/runtime.py`, `channels/whatsapp/runtime.py`, `session/manager.py`, `gateway/runtime.py`, `webui/trading_api.py` وملفات webui أخرى، `cli/*` — 38 ملفاً |
| 018 | `nanobot/config/loader.py` | قراءة/كتابة `config.json`، دمج الافتراضيات، استيفاء `${ENV}`، ترحيل المخطط | `load_config`, `save_config`, `get_config_path`, `set_config_path`, `resolve_config_env_vars`, `resolve_env_refs`, `merge_missing_defaults`, `_migrate_config` | `pydantic`, `nanobot.config.schema.Config`, `nanobot.config.errors`, `nanobot.utils.helpers._write_text_atomic`, `nanobot.security.network.configure_ssrf_whitelist` | 63 ملفاً منها `nanobot/nanobot.py`, `channels/manager.py`, `channels/base.py`, `optional_features.py`, معظم `cli` و`webui/settings*` |
| 019 | `nanobot/config/schema.py` | مخطط Pydantic الكامل: وكلاء، مزودون، قنوات، gateway، أدوات، API | `Config`, `AgentsConfig`, `AgentDefaults`, `ProvidersConfig`, `ProviderConfig`, `ChannelsConfig`, `GatewayConfig`, `ApiConfig`, `ToolsConfig`, `MCPServerConfig`, `DreamConfig`, `HeartbeatConfig`, `ModelPresetConfig`, `TranscriptionConfig` | `pydantic`, `pydantic_settings`, `nanobot.config_base.Base`, `nanobot.providers.registry`, `nanobot.config.timezone` | 139 مستورداً — كل مسار يحمّل الإعداد |
| 020 | `nanobot/config/errors.py` | أخطاء إعداد قابلة للعرض للمستخدم | `ConfigIssue`, `ConfigLoadError`, `validation_issues` | `pydantic.ValidationError` | `nanobot/config/loader.py`, `nanobot/cli/runtime_config.py`, `nanobot/cli/commands.py`؛ 6 اختبارات config |
| 021 | `nanobot/config/timezone.py` | اكتشاف المنطقة الزمنية للنظام | `detect_system_timezone`, `_UTC_ALIASES` | `zoneinfo.ZoneInfo`, `tzlocal.get_localzone_name` | `nanobot/config/schema.py`, `tests/config/test_timezone.py` |
| 022 | `nanobot/config/watcher.py` | مراقبة تغيير ملف الإعداد وإعادة التحميل | `watch_config_file` | `watchfiles.awatch` | `nanobot/cli/gateway_runtime.py`, `tests/config/test_watcher.py` |
| 023 | `nanobot/agent/loop.py` | محرّك الدورات: يستقبل InboundMessage، يبني السياق، يشغّل AgentRunner، يسلّم للخارج. هنا يُحقن Fast Path الذهب و`gold_intent_runtime_context` | `AgentLoop`, `TurnKind`, `TurnContext` | `AgentRunner`, `ToolRegistry`, `RequestContext`, `MessageBus`, `SessionManager`, `SubagentManager`, `Consolidator`, `AutoCompact` وكثير من وحدات الوكيل | 51 ملفاً: `nanobot/nanobot.py`, `cli/gateway_runtime.py`, `cli/commands.py`, `cli/agent.py`, `api/server.py` + اختبارات `tests/agent/*` |
| 024 | `nanobot/agent/runner.py` | حلقة أداة واحدة: طلب LLM → تنفيذ أدوات → إعادة حتى النهاية أو الميزانية | `AgentRunner`, `AgentRunSpec`, `AgentRunResult` | `LLMProvider`, `ToolRegistry`, `execute_tool_calls`, `ContextGovernor`, قوالب الإكمال | `nanobot/agent/loop.py`, `nanobot/agent/subagent.py`؛ 18 اختبار runner |
| 025 | `nanobot/nanobot.py` | واجهة SDK: `Nanobot.run` / `run_streamed` | `Nanobot` (`from_config`, `run`, `run_streamed`, `stream`, `aclose`) | `AgentLoop`, `Config`, `MCPProvider`, `SDK` clients/streaming | `tests/test_nanobot_facade.py`, `tests/agent/test_session_model_runtime.py`؛ مستخدمو SDK الخارجيون |
| 026 | `nanobot/bus/__init__.py` | تصدير الحافلة | يعيد `InboundMessage`, `OutboundMessage`, `MessageBus` | `nanobot.bus.events`, `nanobot.bus.queue` | 122 مستورداً (`from nanobot.bus import`) |
| 027 | `nanobot/bus/queue.py` | طوابير وارد/صادر وأحداث مكتوبة بين القنوات والوكيل | `MessageBus.publish_inbound/outbound/event`, `consume_*`, `subscribe` | `InboundMessage`, `OutboundMessage`, `outbound_message_for_event` | 87 ملفاً: كل القنوات، `AgentLoop`, `cli/agent.py`, `gateway_runtime.py`, `trading/fast_path.py`, `trading/stage_delivery.py` |
| 028 | `nanobot/bus/events.py` | رسائل الحافلة ومفاتيح metadata | `InboundMessage`, `OutboundMessage`؛ ثوابت `OUTBOUND_META_AGENT_UI`, `INBOUND_META_USER_SHELL`, `RUNTIME_CONTROL_*` | `dataclasses`, `nanobot.events.AgentEvent` | 84 ملفاً منها `trading/fast_path.py`, `stage_delivery.py`, كل `channels/*/runtime.py` |
| 029 | `nanobot/bus/runtime_events.py` | أحداث حالة التشغيل (بداية دورة، استخدام LLM، تغيير النموذج) | `RuntimeEventPublisher`, `SessionTurnStarted`, `TurnCompleted`, `SessionTurnPersisted`, `RuntimeModelChanged` | `MessageBus`, `LLMUsage`, `InboundMessage` | `nanobot/agent/turn_delivery.py`, `session/webui_turns.py`, `sdk/clients.py`, `agent/tools/long_task.py` |
| 030 | `nanobot/bus/notification_delivery.py` | سياسة جمهور إشعارات التقدم/التعديل | `notification_is_deliverable`, `NOTIFICATION_AUDIENCES` | أحداث `outbound_events` و`nanobot.events` | `nanobot/agent/turn_delivery.py`, `tests/bus/test_notifications.py` |
| 031 | `nanobot/bus/outbound_events.py` | أحداث صادرة مكتوبة تُلفّ داخل `OutboundMessage` | `ProgressEvent`, `StreamDeltaEvent`, `StreamEndEvent`, `FileEditEvent`, `TurnEndEvent`, `GoalStatusEvent`, `SessionUpdatedEvent`, `outbound_message_for_event` | `OutboundMessage`, `AgentEvent`, `LLMUsage` | 41 ملفاً: `trading/stage_delivery.py`, `channels/telegram/runtime.py`, `whatsapp/runtime.py`, `websocket/runtime.py`, `channels/manager.py` |
| 032 | `nanobot/session/manager.py` | تخزين جلسات JSONL، ترحيل، قفل، أرشفة، استرجاع | `SessionManager`, `Session`, `SessionStore`, `JsonlSessionStore`, `SessionInfo`, `SessionRestoreResult` | `filelock`, `nanobot.config.paths`, `ProviderConversationState`, سياسات الإخفاء والملخص | 68 ملفاً: `AgentLoop`, `cli/commands.py` (restore-workspace), معظم `webui/session_*`, أدوات sessions |
| 033 | `nanobot/agent/tools/registry.py` | سجل الأدوات: تسجيل، مخطط، تنفيذ، اقتراح الاسم | `ToolRegistry` (`register`, `get`, `execute`, `get_definitions`, `prepare_call`)؛ `is_tool_error_result` | `Tool`, `ToolResult`, `current_request_context` | `AgentLoop`, `AgentRunner`, `nanobot.py`, `cli/gateway_runtime.py`, `cli/commands.py`, `cli/agent.py`, `webui/mcp_*` |
| 034 | `nanobot/agent/tools/loader.py` | اكتشاف الأدوات. في هذا المنتج يُسمح فقط بـ `_GOLD_AGENT_MODULES`: `trading_chart`, `trading_team`, `web`, `message`, `spawn`, `cron`, `long_task`, `sessions`, `session_messages`. أدوات الترميز (`shell`, `filesystem`, …) في `_SKIP_MODULES` | `ToolLoader.discover/load`؛ `_GOLD_AGENT_MODULES`, `_SKIP_MODULES` | `pkgutil`, `importlib`, `Tool`, `ToolRegistry` | `nanobot/agent/loop.py`, `nanobot/agent/subagent.py`, `nanobot/agent/tools/__init__.py`؛ اختبارات tool loader |
| 035 | `nanobot/agent/tools/context.py` | سياق الطلب الحالي: `session_key`, القناة، نص المشغّل، `LLMRuntime` | `RequestContext`, `ToolContext`, `ContextAware`؛ `bind_request_context`, `current_request_context`, `current_request_session_key` | `MessageBus`, `SessionManager`, `LLMRuntime`, `CronService`, `ProviderSnapshot` | إنتاج تداول: `trading/orchestrator.py`, `fast_path.py`, `gold_intent_context.py`, `agents/synthesizer.py` + 51 ملفاً آخر |
| 036 | `nanobot/providers/registry.py` | كتالوج مزودي LLM (Anthropic, OpenAI-compat, Bedrock, …) | `PROVIDERS`, `ProviderSpec`, `ProviderModelSpec`, `find_by_name`, `create_dynamic_spec` | `dataclasses`, `pydantic.alias_generators` | `nanobot/config/schema.py`, `cli/commands.py`, `cli/onboard.py`, `cli/provider.py`, `webui/settings_models.py`, `webui/settings_capabilities.py` |
| 037 | `nanobot/channels/registry.py` | اكتشاف حزم القنوات (`telegram`, `whatsapp`, `websocket`) وتحميل الـ runtime كسولاً | `discover_plugins`, `discover_all`, `discover_enabled`, `load_channel_class`, `load_channel_plugin`, `channel_default_enabled` | `pkgutil`, `nanobot.channels.plugin` | `nanobot/channels/manager.py`, `cli/commands.py`, `cli/onboard.py`, `optional_features.py`, `webui/settings_routes.py`, `scripts/install_channel_dependencies.py` |
| 038 | `nanobot/channels/manager.py` | تشغيل/إيقاف القنوات، توصيل الصادر، إعادة التحميل، إشعارات إعادة التشغيل | `ChannelManager` (`start_all`, `stop_all`, `apply_channel_feature_action`, `_start_channel`, `_stop_channel`) | `MessageBus`, `BaseChannel`, `discover_plugins`, `load_channel_plugin`, `WebSocketConfig`, `build_gateway_services` | `nanobot/cli/gateway_runtime.py`؛ 6 اختبارات channel manager |
| 039 | `nanobot/channels/base.py` | العقد المجرّد لكل قناة: start/stop/send/login/pairing/transcription | `BaseChannel` (`start`, `stop`, `send`, `login`, `_handle_message`, `is_allowed`, `send_delta`, `transcribe_audio`) | `MessageBus`, `InboundMessage`, `OutboundMessage`, `nanobot.pairing` | `telegram/runtime.py`, `whatsapp/runtime.py`, `websocket/runtime.py`, `channels/manager.py`, `channels/registry.py`, `channels/plugin.py` |
| 040 | `scripts/deploy-nanoagent-vps.sh` | نشر معزول إلى `/opt/nanoagent`: fetch الفرع، venv، bun build، systemd `nanoagent-gateway`، nginx، certbot. لا يلمس `/opt/foxagent` | دوال bash: `git_safe`؛ سكربت بعيد يكتب الوحدة والمنفذ 8766/18791 | يعتمد على env: `VPS`, `VPSPASS`, `NANOAGENT_BRANCH`, `NANOAGENT_WEB_TOKEN`, `NANOAGENT_DOMAIN` (أسماء فقط) | تشغيل يدوي/وكيل للنشر |
| 041 | `Dockerfile` | صورة متعددة المراحل: Node 24 يبني WebUI؛ uv+Python 3.12 يشغّل `nanobot` | مراحل `webui-builder` ثم runtime | `node:24-bookworm-slim`, `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` | `docker-compose.yml` |
| 042 | `entrypoint.sh` | إسقاط صلاحيات إلى مستخدم `nanobot`؛ على Render ينسخ `render-config.json` إن لم يوجد | منطق `RENDER=true` و`setpriv` | shell فقط | `Dockerfile` ENTRYPOINT |
| 043 | `docker-compose.yml` | خدمات `nanobot-gateway` (18790/8765)، `nanobot-api` (8900)، `nanobot-cli` | YAML خدمات | يبني من `Dockerfile` | تشغيل محلي بالحاويات |

---

## 2. القنوات وواجهة التداول HTTP (044–062)

| # | المسار | الوظيفة | الكلاسات / الدوال الرئيسية | Imports | يُستخدم بواسطة |
|---:|---|---|---|---|---|
| 044 | `nanobot/channels/telegram/runtime.py` | قناة تيليجرام: polling/webhook، HTML، تحرير رسالة التقدم مكانها، إرسال بطاقة التوصية مرة واحدة | `TelegramChannel`, `TelegramConfig`, `_LivenessTrackedRequest`, `_StreamBuf`؛ ثوابت طول الرسالة و`POLL_STALE_SECONDS` | `python-telegram-bot`, `BaseChannel`, `TRADING_PROGRESS_META`, `TRADING_CARD_SENT_META`, `OutboundMessage`, `ProgressEvent` | `nanobot/channels/telegram/tests/test_telegram_channel.py`؛ يُحمَّل عبر `manifest.py` → registry |
| 045 | `nanobot/channels/telegram/trading_cards.py` | يغلّف بطاقة التوصية بصيغة HTML لتيليجرام | `render_recommendation_card` | `nanobot.trading.cards.format.render_telegram_card` | `nanobot/trading/fast_path.py`, `nanobot/trading/stage_delivery.py` |
| 046 | `nanobot/channels/telegram/trading_progress.py` | قائمة مراحل عربية تُحدَّث سطراً بسطر | `TelegramStageRow`؛ `render_arabic_progress`, `apply_stage_event`, `stage_arabic_label`؛ مفاتيح `TRADING_PROGRESS_META`, `TRADING_CARD_SENT_META` | `nanobot.trading.stage_events` | `telegram/runtime.py`, `whatsapp/runtime.py`, `trading/stage_delivery.py`, `tests/trading/test_stage_delivery_channels.py` |
| 047 | `nanobot/channels/telegram/validation.py` | التحقق من توكن/بروكسي تيليجرام عند الإعداد | `validate`, `_get_me`, `_proxy_url_is_valid` | `httpx`, `nanobot.channels.validation`, `resolve_env_refs` | `nanobot/channels/telegram/manifest.py` |
| 048 | `nanobot/channels/telegram/manifest.py` | عقد الإضافة: `PLUGIN`, `SETUP_SPEC` | ثوابت `PLUGIN`, `SETUP_SPEC` | `ChannelPlugin`, `ChannelSetupSpec`, `validate` | `nanobot/channels/telegram/tests/test_validation.py`؛ يكتشفه `registry.discover_plugins` |
| 049 | `nanobot/channels/telegram/__init__.py` | علامة حزمة القناة (وثيقة سطر واحد) | لا رموز | لا استيرادات | مستورد ضمنياً عند تحميل الحزمة (8 مراجع مسار) |
| 050 | `nanobot/channels/whatsapp/runtime.py` | قناة واتساب عبر neonize: QR، رسائل، وسائط؛ يستخدم نفس مفاتيح تقدم التداول | `WhatsAppChannel`, `WhatsAppConfig`, `_NeonizeAPI` | `neonize`, `BaseChannel`, `TRADING_PROGRESS_META`, `PinnedDNSAsyncTransport`, `segno` | `whatsapp/connect.py`, `whatsapp/tests/test_whatsapp_channel.py` |
| 051 | `nanobot/channels/whatsapp/trading_cards.py` | بطاقة توصية نص عادي لواتساب | `render_recommendation_card` | `nanobot.trading.cards.format.render_whatsapp_card` | `nanobot/trading/fast_path.py`, `nanobot/trading/stage_delivery.py` |
| 052 | `nanobot/channels/whatsapp/state.py` | هل توجد جلسة واتساب محفوظة محلياً | `local_state_present` | `channel_field_value`, `get_config_path` | `whatsapp/manifest.py` |
| 053 | `nanobot/channels/whatsapp/validation.py` | تحقق إعداد واتساب | `validate` | `nanobot.channels.validation` | `whatsapp/manifest.py` |
| 054 | `nanobot/channels/whatsapp/connect.py` | تدفق QR التفاعلي من WebUI/CLI | `WhatsAppConnectStore`, `WhatsAppConnectSession` | `WhatsAppChannel`, `MessageBus`, `load_config` | `whatsapp/tests/test_connect.py`؛ مسارات connect في WebUI |
| 055 | `nanobot/channels/whatsapp/manifest.py` | عقد إضافة واتساب | `PLUGIN`, `SETUP_SPEC` | `ChannelPlugin`, `local_state_present`, `validate` | يكتشفه registry (لا استيراد Python مباشر آخر في المسح) |
| 056 | `nanobot/channels/whatsapp/__init__.py` | علامة حزمة واتساب | لا رموز | لا استيرادات | 6 مراجع مسار |
| 057 | `nanobot/channels/websocket/runtime.py` | خادم WebSocket + ربط WebUI: إطارات واردة/صادرة، token، إسقاط أحداث التداول `OUTBOUND_META_AGENT_UI` | `WebSocketChannel`, `WebSocketConfig`, `TrustedProxyAuthConfig`, `_ConnectionOutbound` | `websockets`, `BaseChannel`, `WebUIOutboundProjector`, `GatewayServices`, `ProgressEvent` | `channels/manager.py`, `webui/ws_http.py`, `webui/gateway_endpoint.py`, `webui/gateway_services.py`, `cli/webui_support.py` + 15 اختبار websocket/webui |
| 058 | `nanobot/channels/websocket/validation.py` | تحقق إعداد WebSocket | `validate` | `nanobot.channels.validation` | `websocket/manifest.py` |
| 059 | `nanobot/channels/websocket/manifest.py` | عقد إضافة WebSocket | `PLUGIN`, `SETUP_SPEC` | `ChannelPlugin`, `validate` | يكتشفه registry |
| 060 | `nanobot/channels/websocket/__init__.py` | علامة حزمة WebSocket | لا رموز | لا استيرادات | 22 مرجعاً |
| 061 | `nanobot/webui/trading_api.py` | مسارات HTTP `/api/trading/*`: شموع، سعر، تحليل، توصيات، paper، حالة runtime | `handle_trading_klines`, `handle_trading_quote`, `handle_trading_analyze`, `handle_trading_recommendations`, `handle_trading_performance`, `handle_trading_briefing`, `handle_trading_paper`, `handle_trading_status`, `handle_trading_runtime_update`, `dispatch_trading_route` | `run_unified_chart_agent`, `fetch_candles`, `fetch_quote`, `load_trading_config`, `result_to_wire`, `get_runtime_store`, `list_recommendations`, `run_swarm`, `run_debate_crew` | `nanobot/webui/ws_http.py`, `tests/trading/test_trading_api.py` |
| 062 | `nanobot/webui/ws_http.py` | موزّع HTTP على قناة WebSocket: جلسات، إعدادات، توكن، و`dispatch_trading_route` | `GatewayHTTPHandler.dispatch` وعدد كبير من `_handle_*` | `SessionManager`, `GatewayTokenStore`, وحدات `nanobot.webui.*`، ويستدعي trading_api | `webui/gateway_services.py`, `webui/gateway_endpoint.py`؛ اختبارات webui HTTP |

---

## 3. مدخل محرّك التداول حتى أسطول البيانات (063–085)

| # | المسار | الوظيفة | الكلاسات / الدوال الرئيسية | Imports | يُستخدم بواسطة |
|---:|---|---|---|---|---|
| 063 | `nanobot/trading/__init__.py` | تصدير حارس الذهب | يعيد `DATA_SYMBOL`, `GoldOnlyError`, `is_gold`, `require_gold`, `coerce_to_gold` | `nanobot.trading.gold` | 65 ملفاً داخل `nanobot/trading/*` واختبارات `tests/trading/*` |
| 064 | `nanobot/trading/config.py` | إعداد OANDA من البيئة: `OANDA_API_TOKEN`, `OANDA_ACCOUNT_ID`, `OANDA_ENV` → `practice` أو `live` base URL | `TradingConfig` (`oanda_configured`, `oanda_base_url`)؛ `load_trading_config` | `os`, `dataclasses` | `oanda.py`, `market_context.py`, `fast_path.py`, `webui/trading_api.py`, `agent/tools/trading_chart.py` |
| 065 | `nanobot/trading/cron.py` | تسجيل وظائف مراقبة الذهب على CronService | `register_trading_cron_jobs`, `run_gold_scan_job`, `run_gold_news_job`, `run_gold_followup_job`؛ IDs `GOLD_SCAN_JOB_ID`, `GOLD_NEWS_JOB_ID`, `GOLD_FOLLOWUP_JOB_ID` | `CronJob`, `run_bot_cycle`, `run_news_macro_agent`, `latest_open_recommendation` | `nanobot/cli/gateway_runtime.py` |
| 066 | `nanobot/trading/fast_path.py` | يتجاوز لفّ LLM العام لنيات السعر/التحليل عالية الثقة: سعر مباشر أو `run_unified_chart_agent` + بطاقة | `try_gold_fast_path`, `_run_analysis_fast_path`, `_format_price_response`, `_outbound_from_wire`؛ عتبات `_PRICE_CONFIDENCE_MIN=0.70`, `_ANALYSIS_CONFIDENCE_MIN=0.75` | `plan_turn`, `run_unified_chart_agent`, `fetch_quote`, `TradingStagePublisher`, بطاقات telegram/whatsapp | `nanobot/agent/loop.py`, `tests/trading/test_fast_path.py` |
| 067 | `nanobot/trading/gold.py` | حارس الأداة الواحدة: `XAUUSD` / OANDA `XAU_USD` | `GoldOnlyError`؛ `is_gold`, `require_gold`, `coerce_to_gold`؛ `DATA_SYMBOL`, `OANDA_INSTRUMENT`, `DISPLAY_NAME_EN`, `DISPLAY_NAME_AR` | لا تبعيات خارجية | `oanda.py`, `orchestrator.py`, `fast_path.py`, `trading_api.py`, `trading_chart.py`, `followup.py`, `multi_timeframe.py`, `tests/trading/test_gold.py` |
| 068 | `nanobot/trading/gold_intent_context.py` | يحقن تلميح النية وأدوات الذهب في سياق دورة الوكيل | `gold_intent_plan`, `gold_intent_runtime_context`, `_MODE_TOOL_HINTS` | `plan_turn`, `latest_live_recommendation`, `RequestContext`, `RuntimeContextBlock` | `nanobot/agent/loop.py`, `tests/trading/test_gold_intent_context.py` |
| 069 | `nanobot/trading/intent_router.py` | تصنيف الرسالة: `price_query` / `gold_analysis` / `recommendation` / `team_swarm` / `general_chat` بأنماط إنجليزية وعربية | `RoutedIntent`؛ `route_intent`, `resolve_team_preset` | `re`, `dataclasses` | `turn_planner.py`, `fast_path.py`, `tests/trading/test_intent_router.py`, `tests/trading/test_fast_path.py` |
| 070 | `nanobot/trading/market_context.py` | يحوّل شموع/اقتباس OANDA إلى `AgentMarketContext` + ATR + `MarketSync` | `build_agent_market_context`, `_to_candle` | `fetch_candles`, `fetch_quote`, `compute_atr`, `require_gold` | `agents/market_data.py`, `agents/multi_timeframe.py`, `bots/coordinator.py` |
| 071 | `nanobot/trading/oanda.py` | عميل OANDA v20 للقراءة فقط: شموع واقتباس `XAU_USD` عبر REST `httpx` | `OandaCandle`, `OandaQuote`؛ `fetch_candles`, `fetch_quote`, `candle_to_wire`, `to_oanda_granularity`؛ خرائط `GRANULARITY`, `BAR_DURATION_MS` | `httpx`, `TradingConfig`, `OANDA_INSTRUMENT` | `orchestrator.py`, `fast_path.py`, `market_context.py`, `followup.py`, `trading_api.py`, `trading_chart.py`, `bots/coordinator.py` |
| 072 | `nanobot/trading/orchestrator.py` | منسّق Lonora: متابعة خطة حيّة أو أسطول متوازٍ → أخبار → هندسة → مخاطر مرشحة → بصري → synthesizer → بوابات → رسوم → تخزين | `run_unified_chart_agent`, `_wait_decision`, `_session_key`, `_operator_text` | كل `run_*_agent`, `run_final_decision_synthesizer`, `build_gates`, `run_gate_chain`, `apply_g7_reprice_loop`, `store_recommendation`, `derive_cards` | `fast_path.py`, `trading_chart.py`, `trading_api.py`, `teams/runtime.py`, `crew/debate.py`, `tests/trading/test_orchestrator.py`, `tests/trading/test_lonora_cognition.py` |
| 073 | `nanobot/trading/paper.py` | دفتر ورقي JSON تحت `get_data_dir()/trading` | `record_paper_action`؛ `_LEDGER` | `json`, `get_data_dir` | `nanobot/webui/trading_api.py` (`handle_trading_paper`) |
| 074 | `nanobot/trading/result_wire.py` | تحويل `AgentFinalResult` إلى dict للـ WebUI والأدوات والقنوات | `result_to_wire`, `_jsonable` | `dataclasses.asdict`, `AgentFinalResult` | `fast_path.py`, `trading_api.py`, `trading_chart.py`, `trading_team.py` |
| 075 | `nanobot/trading/runtime_state.py` | حالة عملية: `paused`, `kill_switch`, وضع paper — تُحفظ JSON | `TradingRuntimeStore`, `TradingRuntimeState`, `get_runtime_store` | `get_data_dir`, `threading` | `orchestrator.py` (يرفض عند kill_switch)، `trading_api.py` |
| 076 | `nanobot/trading/stage_checkpoint.py` | تجزئة الشموع لاستئناف الأسطول إن لم يتغير الكندل | `StageCheckpoint`, `candle_hash`, `should_resume` | `hashlib`, `AgentMarketContext` | لا مستورد إنتاجي في المسح الحالي (مرشح لمرحلة 6 Dead Code إن بقي بلا ربط) |
| 077 | `nanobot/trading/stage_delivery.py` | نشر المراحل: WebUI `agent_ui`، تيليجرام checklist تحريري، واتساب سطر واحد ثم بطاقة | `TradingStagePublisher` (`sync_emit`, `publish_result`, `open_chart`, `flush`) | `OutboundMessage`, `ProgressEvent`, `render_arabic_progress`, بطاقات telegram/whatsapp | `fast_path.py`, `trading_chart.py`, `trading_team.py`, `tests/trading/test_stage_delivery_channels.py`, `tests/trading/test_trading_tools.py` |
| 078 | `nanobot/trading/stage_events.py` | تعريف المراحل وتسميات EN/AR: market_data, structure, liquidity, supply_demand, multi_timeframe, news, risk, research, final_decision, drawing | `StageEvent`, `emit_stage`, `stage_label`؛ `KNOWN_STAGES`, `STAGE_LABEL_EN`, `STAGE_LABEL_AR` | `dataclasses` | `orchestrator.py`, `stage_delivery.py`, `telegram/trading_progress.py`, `crew/debate.py` |
| 079 | `nanobot/trading/turn_planner.py` | يقرر وضع الدورة: `full_analysis` / `recommendation_followup` / `specialist` / `conversation` / `reevaluation` / `market_data_only` / `team_swarm` — خطة حيّة واحدة | `TurnPlan`, `TurnTools`؛ `plan_turn`, `wants_explicit_new_analysis` | `route_intent`, `RoutedIntent` | `fast_path.py`, `gold_intent_context.py`, `tests/trading/test_lonora_cognition.py`, `tests/trading/test_fast_path.py` |
| 080 | `nanobot/trading/types.py` | كل أنواع السلك: سوق، نتائج الأسطول، بوابات، توصية، أدلة، رسوم | 31 dataclass منها `AgentMarketContext`, `AgentRecommendation`, `FinalDecisionResult`, `AgentFinalResult`, `EvidenceSnapshot`, `EntryPlan`, `GateChainResult`, `VisualReview`, `DecisionTrace` | `dataclasses`, `typing.Literal` | 36 ملفاً — كل طبقة التداول |
| 081 | `nanobot/trading/agents/__init__.py` | علامة حزمة المتخصصين | لا رموز | لا استيرادات | 6 مراجع مسار |
| 082 | `nanobot/trading/agents/apply_model_decision.py` | إجبار حتمي بعد JSON النموذج: اتجاه معلّق على الأدلة، مستويات معلّقة على السعر، stop buffer/floor، pin للمسار، `apply_revision` نفس الاتجاه | `apply_model_decision`, `apply_revision`, `infer_direction_from_evidence`, `resolve_plan_levels`, `apply_stop_buffer`, `apply_stop_floor`, `pin_scenario_path`, `entry_print_state`؛ `GOLD_FOLLOW_THROUGH_POINTS` | `nanobot.trading.types` | `agents/synthesizer.py`, `tests/trading/test_lonora_cognition.py` |
| 083 | `nanobot/trading/agents/evidence.py` | تجميد `modelContext` JSON للأدلة قبل الـ LLM | `build_evidence_snapshot`, `_level_prices` | `asdict` + أنواع الأسطول و`VisualReview` | `agents/synthesizer.py` |
| 084 | `nanobot/trading/agents/liquidity.py` | متخصص السيولة: مستويات متساوية وعمليات sweep | `run_liquidity_agent` | `find_swings`, `find_equal_levels`, `detect_sweeps`, `LiquidityResult` | `orchestrator.py` (مع `asyncio.gather`) |
| 085 | `nanobot/trading/agents/market_data.py` | غلاف رقيق لاستدعاء `build_agent_market_context` | `run_market_data_agent` | `build_agent_market_context`, `AgentMarketContext` | `orchestrator.py` (أول مرحلة بعد kill_switch) |

---

## 4. ملاحظات للمهندس قبل المرحلة 3

1. `ToolLoader` في هذا الفرع ذهب-فقط: لا تُكتشف أدوات `shell`/`filesystem` حتى لو بقيت ملفاتها على القرص.
2. `try_gold_fast_path` يُستدعى من `AgentLoop` قبل حلقة الأدوات العامة؛ لذلك «اعطيني توصية» لا تمرّ عبر لفّ LLM لأداة `analyze_gold`.
3. `TradingConfig` يقرأ أسماء `OANDA_*` من البيئة فقط — القيم غير موثّقة هنا.
4. `stage_checkpoint.py` بلا مستورد إنتاجي في هذا المسح؛ يُعاد تقييمه في المرحلة 6.
5. الجزء ب يبدأ من متخصصي `multi_timeframe` ثم الأخبار والمخاطر و`synthesizer` والبوابات والرسوم والتخزين وأدوات الوكيل وواجهات `webui/src/components/trading/*` واختبارات `tests/trading/*`.

---

## 5. قائمة ملفات الجزء ب (للمرحلة 3 — لا تحليل هنا)

| # | المسار |
|---:|---|
| 086 | `nanobot/trading/agents/multi_timeframe.py` |
| 087 | `nanobot/trading/agents/news_macro.py` |
| 088 | `nanobot/trading/agents/risk.py` |
| 089 | `nanobot/trading/agents/structure.py` |
| 090 | `nanobot/trading/agents/supply_demand.py` |
| 091 | `nanobot/trading/agents/synth_prompt.py` |
| 092 | `nanobot/trading/agents/synthesizer.py` |
| 093 | `nanobot/trading/agents/visual_capture.py` |
| 094 | `nanobot/trading/bots/__init__.py` |
| 095 | `nanobot/trading/bots/coordinator.py` |
| 096 | `nanobot/trading/cards/__init__.py` |
| 097 | `nanobot/trading/cards/derive.py` |
| 098 | `nanobot/trading/cards/format.py` |
| 099 | `nanobot/trading/crew/__init__.py` |
| 100 | `nanobot/trading/crew/debate.py` |
| 101 | `nanobot/trading/drawings/__init__.py` |
| 102 | `nanobot/trading/drawings/plan.py` |
| 103 | `nanobot/trading/gates/__init__.py` |
| 104 | `nanobot/trading/gates/build_gates.py` |
| 105 | `nanobot/trading/gates/chain.py` |
| 106 | `nanobot/trading/gates/entry_semantics.py` |
| 107 | `nanobot/trading/gates/news_window.py` |
| 108 | `nanobot/trading/gates/reprice_loop.py` |
| 109 | `nanobot/trading/gates/revalidation.py` |
| 110 | `nanobot/trading/geometry/__init__.py` |
| 111 | `nanobot/trading/geometry/detectors.py` |
| 112 | `nanobot/trading/geometry/snapshot.py` |
| 113 | `nanobot/trading/memory/__init__.py` |
| 114 | `nanobot/trading/memory/decisions.py` |
| 115 | `nanobot/trading/news/__init__.py` |
| 116 | `nanobot/trading/news/forex_factory.py` |
| 117 | `nanobot/trading/recommendations/__init__.py` |
| 118 | `nanobot/trading/recommendations/followup.py` |
| 119 | `nanobot/trading/recommendations/store.py` |
| 120 | `nanobot/trading/recommendations/tradability.py` |
| 121 | `nanobot/trading/teams/models.py` |
| 122 | `nanobot/trading/teams/runtime.py` |
| 123 | `nanobot/trading/teams/presets/gold_analysis_committee.yaml` |
| 124 | `nanobot/trading/teams/presets/gold_debate_desk.yaml` |
| 125 | `nanobot/trading/teams/presets/gold_mtf_panel.yaml` |
| 126 | `nanobot/trading/teams/presets/gold_news_war_room.yaml` |
| 127 | `nanobot/agent/tools/trading_chart.py` |
| 128 | `nanobot/agent/tools/trading_team.py` |
| 129 | `nanobot/skills/gold-trading/SKILL.md` |
| 130 | `nanobot/skills/README.md` |
| 131 | `nanobot/skills/memory/SKILL.md` |
| 132 | `nanobot/skills/cron/SKILL.md` |
| 133 | `webui/src/main.tsx` |
| 134 | `webui/src/App.tsx` |
| 135 | `webui/src/components/trading/TvChart.tsx` |
| 136 | `webui/src/components/trading/GoldChartPanel.tsx` |
| 137 | `webui/src/components/trading/TradingRecommendationCard.tsx` |
| 138 | `webui/src/components/trading/TradingStageChecklist.tsx` |
| 139 | `webui/src/components/trading/AgentCards.tsx` |
| 140 | `webui/src/components/trading/ChartTradeOverlay.tsx` |
| 141 | `webui/src/components/trading/TradingBriefingPanel.tsx` |
| 142 | `webui/src/components/trading/TradingChartBottomSheet.tsx` |
| 143 | `webui/src/components/trading/TradingChartSidecar.tsx` |
| 144 | `webui/src/components/trading/TradingConnect.tsx` |
| 145 | `webui/src/components/trading/TradingInbox.tsx` |
| 146 | `webui/src/components/trading/TradingPerformance.tsx` |
| 147 | `webui/src/components/trading/TradingStatusBar.tsx` |
| 148 | `webui/src/lib/trading/session-store.ts` |
| 149 | `webui/src/lib/trading/stage-labels.ts` |
| 150 | `webui/src/lib/trading/types.ts` |
| 151 | `webui/package.json` |
| 152 | `webui/public/charting_library/package.json` |
| 153 | `tests/trading/test_lonora_cognition.py` |
| 154 | `tests/trading/test_gold_intent_context.py` |
| 155 | `tests/trading/test_recommendation_cards.py` |
| 156 | `tests/trading/test_intent_router.py` |
| 157 | `tests/trading/test_stage_delivery_channels.py` |
| 158 | `tests/trading/test_fast_path.py` |
| 159 | `tests/trading/test_reprice_loop.py` |
| 160 | `tests/trading/test_teams.py` |
| 161 | `tests/trading/test_orchestrator.py` |
| 162 | `tests/trading/test_forex_factory.py` |
| 163 | `tests/trading/test_trading_tools.py` |
| 164 | `tests/trading/test_decision_memory.py` |
| 165 | `tests/trading/test_gold.py` |
| 166 | `tests/trading/test_stage_events.py` |
| 167 | `tests/trading/test_gates.py` |
| 168 | `tests/trading/test_trading_api.py` |
| 169 | `tests/trading/test_cards.py` |
| 170 | `.env.example` |

