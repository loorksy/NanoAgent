<!-- المرحلة 5 من Master Project Documentation — الإعدادات والتكاملات. لا يحتوي أسراراً من .env. أسماء المتغيرات فقط. -->

# Master Project Documentation — المرحلة 5: الإعدادات والتكاملات

- **نطاق هذه المرحلة:** أسماء متغيرات البيئة (بلا قيم)، ملفات الإعداد، الواجهات الخارجية، HTTP الداخلي للتداول، مخططات التخزين، أوامر التشغيل والتثبيت، Docker، CI، ومسار النشر على VPS.
- **لم يُقرأ:** `.env`. المصدر الوحيد للعيّنات هو `.env.example`. الأسماء الإضافية مأخوذة من `os.environ.get` و`os.environ[` في الشفرة ومن سكربتات المستودع.
- **المراحل السابقة:** `docs/master-project/01-architecture.md`، `02-core-files-a.md`، `03-core-files-b.md`، `04-the-brain.md`.
- **المرحلة التالية (6):** نقاط القوة والضعف، كود ميت، TODO/FIXME، أمن، دين تقني، 10 اقتراحات، خارطة طريق — لا تبدأ إلا بعد «اكمل».
- **قاعدة الأمان:** لا قيم أسرار، لا توكنات، لا كلمات مرور. عيّنة `OANDA_ENV=practice` في `.env.example` اسم بيئة وليست سراً.
- **تحميل البيئة في الإنتاج:** بايثون لا يستدعي `load_dotenv`. systemd يحمّل `/opt/nanoagent/.env` عبر `EnvironmentFile=-/opt/nanoagent/.env`. `config.json` يحلّ `${VAR}` عند التحميل عبر `resolve_env_refs` / `_env_replace` في `nanobot/config/loader.py`.

---

## 1. أسماء متغيرات البيئة

### 1.1 ملف `.env.example` (الموجود في جذر المستودع)

| الاسم | الملف الذي يقرأه | الغرض | إلزامي للمنتج الحي |
|---|---|---|---|
| `OANDA_API_TOKEN` | `nanobot/trading/config.py` | Bearer لـ OANDA v20 REST | نعم لجلب الشموع والسعر |
| `OANDA_ACCOUNT_ID` | `nanobot/trading/config.py` | معرّف الحساب لمسار `/v3/accounts/{id}/pricing` | نعم لـ `fetch_quote` |
| `OANDA_ENV` | `nanobot/trading/config.py` | `live` → `https://api-fxtrade.oanda.com`؛ أي قيمة أخرى أو غياب → `https://api-fxpractice.oanda.com`. العيّنة في `.env.example` هي `practice` | لا؛ الافتراضي `practice` |

`oanda_configured` في `TradingConfig` يساوي وجود `OANDA_API_TOKEN` فقط. غياب `OANDA_ACCOUNT_ID` يبقي الشموع ممكنة ويجعل `fetch_quote` يعيد `None`.

### 1.2 أخبار التداول (في الشفرة وليست في `.env.example`)

| الاسم | الملف | القيم التي تُعدّ مفعّلة | الافتراضي إن غاب |
|---|---|---|---|
| `FOREX_FACTORY_ENABLED` | `nanobot/trading/news/forex_factory.py` و`nanobot/trading/agents/news_macro.py` | `1` أو `true` أو `yes` بعد `strip` | معطّل؛ `fetch_upcoming_events` يعيد `[]` |
| `TRADING_NEWS_STUB` | `nanobot/trading/agents/news_macro.py` | يُلغى stub إذا كانت القيمة `0` أو `false` أو `no` | `"1"` أي stub مفعّل عندما يكون Forex Factory غير حي |

### 1.3 نشر VPS (`scripts/deploy-nanoagent-vps.sh` و`scripts/sync-oanda-from-foxagent.sh`)

| الاسم | إلزامي | الدور |
|---|---|---|
| `VPS` | نعم للسكربتين | مضيف SSH؛ الأمر `sshpass -p "$VPSPASS" ssh -o StrictHostKeyChecking=no "root@${VPS}"` |
| `VPSPASS` | نعم للسكربتين | كلمة مرور SSH لـ `sshpass -p` |
| `NANOAGENT_DOMAIN` | لا | افتراضي `nanoagent.lork.cloud` |
| `NANOAGENT_BRANCH` | لا | افتراضي في السكربت الحالي `main` |
| `NANOAGENT_WEB_TOKEN` | لا | إن غاب يولّد `openssl rand -hex 24` ويُكتب في `channels.websocket.tokenIssueSecret` فقط إن لم يكن موجوداً مسبقاً |

`sync-oanda-from-foxagent.sh` يخرج فوراً إذا كان `OANDA_API_TOKEN` و`OANDA_ACCOUNT_ID` مضبوطين محلياً. وإلا يقرأ من حاوية foxagent (قراءة فقط) ويكتب الأسماء الثلاثة `OANDA_API_TOKEN` و`OANDA_ACCOUNT_ID` و`OANDA_ENV` في `.env` المحلي. لا تُشغّل هذه المزامنة إلا بطلب صريح. لا تُلمس `/opt/foxagent`.

ثوابت السكربت غير البيئية: `INSTALL_DIR=/opt/nanoagent`، `SERVICE_USER=nanoagent`، `WEB_PORT=8766`، `HEALTH_PORT=18791`، `REPO_URL=https://github.com/loorksy/NanoAgent.git`.

### 1.4 تثبيت الحزمة (`scripts/install.sh` و`scripts/install.ps1`)

| الاسم | الدور |
|---|---|
| `NANOBOT_BIN_DIR` | دليل الثنائيات؛ افتراضي `$HOME/.local/bin` (shell فقط) |
| `NANOBOT_VENV` | مسار الـ venv المُدار؛ افتراضي `$HOME/.nanobot/venv` أو `%USERPROFILE%\.nanobot\venv` |
| `NANOBOT_SKIP_WIZARD` | إن ساوى `1` يتخطى `nanobot onboard --wizard` بعد التثبيت |

### 1.5 Docker وRender

| الاسم | المصدر | الدور |
|---|---|---|
| `NANOBOT_EXTRAS` | `Dockerfile` `ARG` | extras لـ `uv pip install ".[${NANOBOT_EXTRAS}]"` |
| `NANOBOT_CHANNELS` | `Dockerfile` `ARG` و`docker-compose.yml` | قائمة قنوات مفصولة بفاصلة تُمرَّر إلى `scripts/install_channel_dependencies.py`؛ افتراضي compose هو `whatsapp` |
| `NANOBOT_SKIP_WEBUI_BUILD` | `Dockerfile` و`nanobot/webui/build.py` و`hatch_build.py` | `1` يتخطى بناء WebUI أثناء تثبيت العجلة |
| `NANOBOT_FORCE_WEBUI_BUILD` | `hatch_build.py` | `1` يعيد بناء `nanobot/web/dist` حتى لو كان `index.html` موجوداً |
| `NANOBOT_WEB_TOKEN` | `render.yaml` و`render-config.json` | يُحقن في `channels.websocket.tokenIssueSecret` عبر `${NANOBOT_WEB_TOKEN}` |
| `ANTHROPIC_API_KEY` | `render.yaml` و`render-config.json` | يُحقن في `providers.anthropic.apiKey` عبر `${ANTHROPIC_API_KEY}` |
| `RENDER` | `entrypoint.sh` | إن ساوى `true` ينسخ `render-config.json` إلى `$HOME/.nanobot/config.json` إن لم يوجد، ويضيف `--config` |
| `PORT` | `render.yaml` | عيّنة Render هي `8765` وتطابق منفذ قناة websocket في القالب |
| `VIRTUAL_ENV` | `Dockerfile` | `/app/.venv` |
| `HOME` | `Dockerfile` ووحدة systemd | Docker: `/home/nanobot`؛ VPS: `/opt/nanoagent` |
| `PATH` | `Dockerfile` ووحدة systemd | يسبق ثنائيات الـ venv |
| `PYTHONUNBUFFERED` | `Dockerfile` | `1` |
| `PYTHONFAULTHANDLER` | `Dockerfile` | `1` |

### 1.6 زمن تشغيل المنصة (تُقرأ في الشفرة)

| الاسم | الملف | الدور |
|---|---|---|
| `NANOBOT_MAX_CONCURRENT_REQUESTS` | `nanobot/agent/loop.py` | عدد صحيح؛ `0` أو غياب = بلا حد |
| `NANOBOT_STREAM_IDLE_TIMEOUT_S` | `nanobot/providers/base.py` (`STREAM_IDLE_TIMEOUT_ENV`) | مهلة خمول البث؛ افتراضي `90.0`؛ سقف `3600.0` |
| `NANOBOT_OPENAI_COMPAT_TIMEOUT_S` | `nanobot/providers/openai_compat_provider.py` | مهلة طلبات OpenAI-compatible |
| `NANOBOT_WORKSPACE_SANDBOX_PROVIDER` | `nanobot/security/workspace_access.py` | مزوّد صندوق الرمل |
| `NANOBOT_WORKSPACE_SANDBOX_ENFORCED` | `nanobot/security/workspace_access.py` | فرض صندوق الرمل |
| `NANOBOT_SANDBOX_ENFORCED` | `nanobot/security/workspace_access.py` | اسم توافق قديم لنفس الفرض |
| `PIP_INDEX_URL` | `nanobot/optional_features.py` | فهرس pip عند تثبيت extras |
| `_NANOBOT_COMPLETE` | `nanobot/cli/entry.py` و`nanobot/cli/desktop_tui.py` و`nanobot/cli/desktop_target.py` | تفعيل إكمال الصدفة لـ Typer |
| `PYTHONIOENCODING` | `nanobot/cli/entry.py` و`nanobot/cli/commands.py` | على Windows يُضبط إلى `utf-8` |
| `SPT_NOENV` | `nanobot/cli/process_identity.py` | `setdefault("SPT_NOENV", "1")` لـ setproctitle |
| `DISPLAY` | `nanobot/webui/native_folder_picker.py` | وجوده (أو `WAYLAND_DISPLAY`) يسمح بانتقاء مجلد أصلي |
| `WAYLAND_DISPLAY` | `nanobot/webui/native_folder_picker.py` | بديل `DISPLAY` |
| `LANG` | `nanobot/apps/cli/service.py` | بيئة أوامر معزولة؛ افتراضي `C.UTF-8` |
| `TERM` | `nanobot/apps/cli/service.py` | افتراضي `dumb` في العزل |
| `COMSPEC` | `nanobot/agent/tools/mcp.py` و`nanobot/apps/cli/service.py` | صدفة Windows لـ MCP stdio |
| `SYSTEMROOT` | `nanobot/apps/cli/service.py` | جذر Windows في العزل |
| `USERPROFILE` | `nanobot/apps/cli/service.py` | عزل Windows |
| `HOMEDRIVE` | `nanobot/apps/cli/service.py` | عزل Windows |
| `HOMEPATH` | `nanobot/apps/cli/service.py` | عزل Windows |
| `TEMP` | `nanobot/apps/cli/service.py` | عزل Windows |
| `TMP` | `nanobot/apps/cli/service.py` | عزل Windows |
| `PATHEXT` | `nanobot/apps/cli/service.py` | عزل Windows |
| `LOCALAPPDATA` | `nanobot/cli/desktop_target.py` | دليل بيانات سطح المكتب إن لم يُضبط `NANOBOT_DESKTOP_DATA_DIR` |

بادئة Pydantic Settings على الجذر `Config` في `nanobot/config/schema.py`:

```
env_prefix="NANOBOT_"
env_nested_delimiter="__"
```

أي حقل في `config.json` يمكن تجاوزه بمتغير مثل `NANOBOT_GATEWAY__PORT` أو `NANOBOT_AGENTS__DEFAULTS__MODEL`. القيم المركّبة يجب أن تكون JSON صالح وإلا يفشل التحميل برسالة `Check that complex NANOBOT_* values use valid JSON.`

### 1.7 TUI وسطح المكتب

| الاسم | الملف | الدور |
|---|---|---|
| `NANOBOT_TUI_BIN` | `nanobot/cli/tui_launcher.py` | مسار ثنائي TUI بديل |
| `NANOBOT_TUI_NO_DOWNLOAD` | `nanobot/cli/tui_launcher.py` | `1` يمنع تنزيل ثنائي TUI |
| `NANOBOT_TUI_THEME` | `nanobot/cli/tui_launcher.py` | يُحقن عند الإطلاق |
| `NANOBOT_TUI_WORKSPACE` | `nanobot/cli/tui_launcher.py` | مساحة عمل TUI |
| `NANOBOT_TUI_BOOTSTRAP_URL` | `nanobot/cli/tui_launcher.py` | `{base}/webui/bootstrap` |
| `NANOBOT_TUI_WS_URL` | `nanobot/cli/tui_launcher.py` | يُحذف ثم يُعاد بناؤه من الإعداد |
| `NANOBOT_TUI_HEALTH_URL` | `nanobot/cli/tui_launcher.py` | صحة البوابة |
| `NANOBOT_TUI_GATEWAY_STOP_COMMAND` | `nanobot/cli/tui_launcher.py` | أمر إيقاف نسخة البوابة |
| `NANOBOT_TUI_BOOTSTRAP_SECRET` | `nanobot/cli/tui_launcher.py` | سر bootstrap إن وُجد |
| `NANOBOT_TUI_API_URL` | `nanobot/cli/tui_launcher.py` | عنوان API للـ TUI |
| `NANOBOT_TUI_API_TOKEN` | `nanobot/cli/tui_launcher.py` | يُحذف عند إعادة الحقن |
| `NANOBOT_TUI_CHAT_ID` | `nanobot/cli/tui_launcher.py` | معرّف محادثة TUI |
| `NANOBOT_TUI_MODEL` | `nanobot/cli/tui_launcher.py` | عرض النموذج |
| `NANOBOT_TUI_MODEL_PRESET` | `nanobot/cli/tui_launcher.py` | اسم الإعداد أو `default` |
| `NANOBOT_TUI_VERSION` | `nanobot/cli/tui_launcher.py` | `__version__` |
| `NANOBOT_TUI_ACCESS` | `nanobot/cli/tui_launcher.py` | مستوى وصول الواجهة |
| `NANOBOT_TUI_DESKTOP_RESOLVER` | `nanobot/cli/desktop_tui.py` | JSON محقون لسطح المكتب |
| `NANOBOT_TUI_DESKTOP_TARGET` | `nanobot/cli/desktop_tui.py` | JSON هدف سطح المكتب |
| `NANOBOT_DESKTOP_CLIENT_CACHE` | `nanobot/cli/desktop_tui.py` | كاش عميل سطح المكتب |
| `NANOBOT_DESKTOP_EXPECTED_INSTANCE` | `nanobot/cli/desktop_tui.py` | نسخة متوقعة |
| `NANOBOT_DESKTOP_ROOT` | `nanobot/cli/desktop_target.py` | جذر تثبيت سطح المكتب |
| `NANOBOT_DESKTOP_DATA_DIR` | `nanobot/cli/desktop_target.py` | تجاوز دليل بيانات سطح المكتب |
| `NANOBOT_API_URL` | `nanobot/webui/dev.py` | يُحقن في عملية Vite sidecar |

### 1.8 إشعار إعادة التشغيل (عملية داخلية تكتب ثم تقرأ)

| الاسم | الثابت في `nanobot/utils/restart.py` |
|---|---|
| `NANOBOT_RESTART_NOTIFY_CHANNEL` | `RESTART_NOTIFY_CHANNEL_ENV` |
| `NANOBOT_RESTART_NOTIFY_CHAT_ID` | `RESTART_NOTIFY_CHAT_ID_ENV` |
| `NANOBOT_RESTART_NOTIFY_METADATA` | `RESTART_NOTIFY_METADATA_ENV` |
| `NANOBOT_RESTART_STARTED_AT` | `RESTART_STARTED_AT_ENV` |

### 1.9 GitHub Copilot (اختياري؛ ليس مسار الذهب)

| الاسم | الملف |
|---|---|
| `NANOBOT_GITHUB_COPILOT_CLIENT_ID` | `nanobot/providers/github_copilot_provider.py` |
| `NANOBOT_GITHUB_DEVICE_CODE_URL` | نفس الملف |
| `NANOBOT_GITHUB_ACCESS_TOKEN_URL` | نفس الملف |
| `NANOBOT_GITHUB_USER_URL` | نفس الملف |
| `NANOBOT_COPILOT_BASE_URL` | نفس الملف |
| `NANOBOT_COPILOT_TOKEN_URL` | نفس الملف |

### 1.10 مفاتيح مزوّدي LLM والبحث والنسخ (أسماء فقط؛ تُقرأ من البيئة إن لم تُذكر في `config.json`)

| الاسم | أين يُستخدم |
|---|---|
| `ANTHROPIC_API_KEY` | قالب Render؛ شائع في `providers.anthropic.apiKey` عبر `${ANTHROPIC_API_KEY}` |
| `OPENAI_API_KEY` | `nanobot/providers/transcription.py` (نسخ OpenAI) |
| `OPENROUTER_API_KEY` | `nanobot/providers/transcription.py` |
| `GROQ_API_KEY` | `nanobot/providers/transcription.py` |
| `OPENAI_TRANSCRIPTION_BASE_URL` | `nanobot/providers/transcription.py` |
| `GROQ_BASE_URL` | `nanobot/providers/transcription.py` |
| `OPENROUTER_BASE_URL` | `nanobot/providers/transcription.py` |
| `ASSEMBLYAI_API_KEY` | `nanobot/providers/transcription.py` |
| `ASSEMBLYAI_BASE_URL` | `nanobot/providers/transcription.py` |
| `MIMO_API_KEY` | `nanobot/providers/transcription.py` |
| `MIMO_API_BASE` | `nanobot/providers/transcription.py` |
| `STEPFUN_API_KEY` | `nanobot/providers/transcription.py` |
| `SILICONFLOW_API_KEY` | `nanobot/audio/transcription.py` |
| `TAVILY_API_KEY` | `nanobot/agent/tools/web.py` و`nanobot/utils/searchusage.py` |
| `BRAVE_API_KEY` | `nanobot/agent/tools/web.py` |
| `JINA_API_KEY` | `nanobot/agent/tools/web.py` (بحث + `r.jina.ai`) |
| `KAGI_API_KEY` | `nanobot/agent/tools/web.py` |
| `EXA_API_KEY` | `nanobot/agent/tools/web.py` |
| `OLOSTEP_API_KEY` | `nanobot/agent/tools/web.py` |
| `BOCHA_API_KEY` | `nanobot/agent/tools/web.py` |
| `SERPER_API_KEY` | `nanobot/agent/tools/web.py` |
| `SEARXNG_BASE_URL` | `nanobot/agent/tools/web.py`؛ إن غاب يسقط البحث إلى DuckDuckGo |
| `KEENABLE_API_KEY` | `nanobot/agent/tools/web.py` |
| `ANYSEARCH_API_KEY` | `nanobot/agent/tools/web.py` |
| `VOLCENGINE_SEARCH_API_KEY` | `nanobot/agent/tools/web.py` |
| `WEB_SEARCH_API_KEY` | `nanobot/agent/tools/web.py` (بديل لـ VolcEngine) |
| `LANGFUSE_SECRET_KEY` | `nanobot/webui/settings_capabilities.py` و`nanobot/providers/openai_compat_provider.py` |
| `LANGFUSE_PUBLIC_KEY` | `nanobot/webui/settings_capabilities.py` |
| `LANGFUSE_BASE_URL` | `nanobot/webui/settings_capabilities.py` |
| `AWS_REGION` | `nanobot/providers/bedrock_provider.py` |
| `AWS_DEFAULT_REGION` | `nanobot/providers/bedrock_provider.py` |
| `AWS_BEARER_TOKEN_BEDROCK` | يُكتب وقت التشغيل في `bedrock_provider.py` من مفتاح الإعداد وليس من `.env.example` |

مهارات الوكيل قد تعلن `required_env_vars` في `SKILL.md`. `nanobot/agent/skills.py` يفحص `os.environ.get(var)` ويعرض `missing_env` دون طباعة القيم.

---

## 2. ملفات الإعداد

### 2.1 المسارات

| المسار | الدور |
|---|---|
| `~/.nanobot/config.json` | الافتراضي عبر `get_config_path()` في `nanobot/config/loader.py` |
| `/opt/nanoagent/.nanobot/config.json` | إنتاج VPS لأن `HOME=/opt/nanoagent` |
| `/opt/nanoagent/.env` | أسماء البيئة فقط؛ يحمّله systemd بـ `EnvironmentFile=-/opt/nanoagent/.env` (الشرطة تعني تجاهل الملف إن غاب) |
| `.env.example` | عيّنة المستودع: `OANDA_API_TOKEN` و`OANDA_ACCOUNT_ID` و`OANDA_ENV` |
| `render-config.json` | قالب Render في جذر المستودع |
| `render.yaml` | Blueprint Render |
| `--config` / `-c` | تجاوز مسار الإعداد في أوامر CLI |

`get_data_dir()` = أب `config.json`. لذلك كل SQLite وJSONL أدناه يعيش بجانب ملف الإعداد لا بجانب الشجرة المصدرية.

الاستيفاء: أي سلسلة `${VAR}` في JSON تُستبدل من `os.environ`. متغير ناقص يرفع `ValueError: Environment variable 'NAME' referenced in config is not set` عند التحميل الكامل، أو يعيد سلسلة فارغة عبر `resolve_env_refs` للحقول الكسولة (مثل مفتاح نسخ).

### 2.2 جذر Pydantic `Config` — `nanobot/config/schema.py`

| الحقل | النوع | الافتراضي البارز |
|---|---|---|
| `agents` | `AgentsConfig` | `defaults: AgentDefaults` |
| `channels` | `ChannelsConfig` (`extra="allow"`) | قنوات مضافة كحقول إضافية: `telegram` و`whatsapp` و`websocket` |
| `transcription` | `TranscriptionConfig` | `enabled=True`، `max_duration_sec=120`، `max_upload_mb=25` |
| `providers` | `ProvidersConfig` (`extra="allow"`) | مفاتيح مضمّنة لكل مزوّد مسجّل + مزوّدون مخصّصون |
| `api` | `ApiConfig` | `host=127.0.0.1`، `port=8900`، `timeout=120.0`؛ ربط `0.0.0.0` يتطلب `api.api_key` غير فارغ |
| `gateway` | `GatewayConfig` | `host=127.0.0.1`، `port=18790`، `restart_mode` أحد `auto`/`exec`/`spawn`/`exit`، `heartbeat.enabled=True` و`interval_s=1800` |
| `tools` | `ToolsConfig` | `web`، `exec`، `file`، `cli_apps`، `my`، `image_generation`، `mcp_servers`، `ssrf_whitelist`، `restrict_to_workspace=False`، `webui_allow_local_service_access=True`، `webui_allow_remote_package_install=False`، `max_session_messages_per_minute=6` |
| `model_presets` / `modelPresets` | `dict[str, ModelPresetConfig]` | الاسم `default` محجوز لـ `agents.defaults` |

`AgentDefaults` البارزة لهذا المنتج:

| الحقل | الافتراضي في الشفرة |
|---|---|
| `workspace` | `~/.nanobot/workspace` |
| `model` | `anthropic/claude-opus-4-5` |
| `provider` | `auto` |
| `max_tokens` | `8192` |
| `context_window_tokens` | `200000` |
| `temperature` | `0.1` |
| `max_tool_iterations` | `200` |
| `max_concurrent_subagents` | `4` |
| `timezone` | `UTC` مع `timezone_mode=auto` يكتشف منطقة النظام |
| `bot_name` | `nanobot` |
| `unified_session` | `False` |
| `session_ttl_minutes` | `15` (اسم التسلسل `idleCompactAfterMinutes`) |
| `dream.enabled` | `True` |
| `dream.interval_h` | `2` |

`ProviderConfig` لكل مزوّد: `display_name`، `api_key`، `api_base`، `api_type` (`auto`/`chat_completions`/`responses`؛ `api_type` غير `auto` مسموح فقط لـ `providers.openai`)، `extra_headers`، `extra_body`، `extra_query`، `proxy`، `thinking_style` (`thinking_type` أو `enable_thinking` أو `reasoning_split`). `BedrockProviderConfig` يضيف `region` و`profile`.

مفاتيح `ProvidersConfig` المضمّنة: `custom`، `azure_openai`، `bedrock`، `anthropic`، `openai`، `openrouter`، `orcarouter`، `assemblyai`، `huggingface`، `skywork`، `deepseek`، `groq`، `zhipu`، `dashscope`، `modelscope`، `vllm`، `ollama`، `lm_studio`، `atomic_chat`، `ovms`، `gemini`، `moonshot`، `kimi_coding`، `minimax`، `minimax_anthropic`، `mistral`، `stepfun`، `xiaomi_mimo`، `longcat`، `ant_ling`، `aihubmix`، `siliconflow`، `edenai`، `novita`، `volcengine`، `volcengine_coding_plan`، `byteplus`، `byteplus_coding_plan`، `openai_codex` (exclude)، `xai_grok` (exclude)، `github_copilot` (exclude)، `qianfan`، `nvidia`، `opencode`، `opencode_zen`، `opencode_go`.

`MCPServerConfig`: `type` (`stdio`/`sse`/`streamableHttp`)، `auth` (`oauth` أو فارغ)، `command`، `args`، `env`، `cwd`، `url`، `headers`، `tool_timeout=30`، `enabled_tools=["*"]`.

### 2.3 قنوات هذا المنتج داخل `channels`

`ChannelsConfig` المشتركة: `send_progress=True`، `send_tool_hints=True`، `show_reasoning=True`، `extract_document_text=True` (مهمل ومُتجاهل)، `send_max_retries=3`، `transcription_provider="groq"` (مهمل)، `transcription_language` (مهمل).

#### `channels.websocket` — `WebSocketConfig` في `nanobot/channels/websocket/runtime.py`

| الحقل | الافتراضي |
|---|---|
| `enabled` | `True` |
| `host` | `127.0.0.1` |
| `port` | `8765` |
| `unix_socket_path` | `""` (مطلق إن وُجد) |
| `path` | `/` |
| `public_ws_url` | `""` |
| `token` | `""` |
| `token_issue_path` | `""` (يجب أن يختلف عن `path`) |
| `token_issue_secret` | `""` (يُقبل `Authorization: Bearer` أو `X-Nanobot-Auth`) |
| `token_ttl_s` | `300` (بين 30 و86400) |
| `websocket_requires_token` | `True` |
| `allow_from` | `["*"]` |
| `streaming` | `True` |
| `max_message_bytes` | `37748736` (سقف `41943040`) |
| `ping_interval_s` | `20.0` |
| `ping_timeout_s` | `20.0` |
| `ssl_certfile` | `""` |
| `ssl_keyfile` | `""` |
| `trusted_proxy_auth` | `None` |

إنتاج VPS يكتب: `enabled=true`، `host=0.0.0.0`، `port=8766`، ويبقي `tokenIssueSecret` إن وُجد وإلا يستخدم `NANOAGENT_WEB_TOKEN`. كذلك `gateway.host=0.0.0.0` و`gateway.port=18791` و`tools.webuiAllowRemotePackageInstall=true`.

#### `channels.telegram` — `TelegramConfig` في `nanobot/channels/telegram/runtime.py`

| الحقل | الافتراضي |
|---|---|
| `enabled` | `False` |
| `token` | `""` (توكن بوت؛ يُخزَّن في `config.json` وليس كاسم بيئة مخصّص) |
| `mode` | `polling` أو `webhook` |
| `allow_from` | `[]` |
| `proxy` | `None` |
| `reply_to_message` | `False` |
| `react_emoji` | `👀` |
| `group_policy` | `mention` (`open` أو `mention`) |
| `connection_pool_size` | `32` |
| `pool_timeout` | `5.0` |
| `streaming` | `True` |
| `inline_keyboards` | `False` |
| `rich_messages` | `False` |
| `stream_edit_interval` | قيمة `_STREAM_EDIT_INTERVAL_DEFAULT` في الملف نفسه |
| `webhook_url` | `""` (إلزامي HTTPS عام عند `mode=webhook`) |
| `webhook_listen_host` | `127.0.0.1` |
| `webhook_listen_port` | `8081` |
| `webhook_path` | `/telegram` |
| `webhook_secret_token` | `""` (إلزامي في وضع webhook؛ 1–256 من `[A-Za-z0-9_-]`) |
| `webhook_max_connections` | `4` |

الاعتماد يُثبَّت على VPS يدوياً: `python-telegram-bot[socks,webhooks]>=22.6,<23.0` مع `socksio` و`python-socks[asyncio]`. لا extra اسمه `telegram` في `pyproject.toml`.

#### `channels.whatsapp` — `WhatsAppConfig` في `nanobot/channels/whatsapp/runtime.py`

| الحقل | الافتراضي |
|---|---|
| `enabled` | `False` |
| `allow_from` | `[]` |
| `group_policy` | `open` |
| `database_path` | `""` → `get_runtime_subdir("whatsapp-auth") / "neonize.db"` |
| `proxy` | `""` |
| `lid_mappings` | `{}` |

الحقول القديمة `bridgeUrl` / `bridgeToken` / `bridge_url` / `bridge_token` مرفوضة. الاعتماد: `neonize>=0.4.3.post0,<0.5.0` و`segno>=1.6.1,<2.0.0`.

### 2.4 `render-config.json` (حرفي كما في المستودع، بلا أسرار)

```json
{
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-8",
      "provider": "auto"
    }
  },
  "providers": {
    "anthropic": {
      "apiKey": "${ANTHROPIC_API_KEY}"
    }
  },
  "gateway": {
    "host": "127.0.0.1",
    "port": 18790
  },
  "channels": {
    "websocket": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8765,
      "tokenIssueSecret": "${NANOBOT_WEB_TOKEN}",
      "websocketRequiresToken": true
    }
  },
  "tools": {
    "restrictToWorkspace": true,
    "webuiAllowRemotePackageInstall": false,
    "my": {
      "allowSet": false
    }
  }
}
```

ملاحظة المنتج: قالب Render يستخدم النموذج `anthropic/claude-opus-4-8`. افتراضي المخطط في الشفرة هو `anthropic/claude-opus-4-5`. إعداد VPS ينشأ عبر `nanobot onboard --yes` ثم يُعدَّل المنفذ والـ token.

### 2.5 extras في `pyproject.toml`

| extra | الحزم |
|---|---|
| `api` | `aiohttp>=3.9.0,<4.0.0` |
| `azure` | `azure-identity>=1.19.0,<2.0.0` |
| `bedrock` | `boto3>=1.43.0` |
| `documents` | `defusedxml`، `pypdf`، `python-docx`، `openpyxl`، `python-pptx` (مُدمجة في الاعتمادات الأساسية منذ v0.2.3) |
| `langfuse` | `langfuse>=3.0.0,<4.0.0` |
| `pdf` | `pypdf>=5.0.0,<6.0.0` |
| `olostep` | `olostep>=0.1.0` عندما `python_version < '3.14'` |
| `dev` | `pytest`، `pytest-asyncio`، `aiohttp`، `pytest-cov`، `pytest-xdist`، `ruff`، `basedpyright`، `pymupdf`، قرّاء المستندات، `python-socketio`، `msgpack` |

سكربتات الحزمة: `nanobot = nanobot.cli.entry:main` و`nanobot-desktop-tui = nanobot.cli.desktop_tui:main`. بايثون `>=3.11`. البناء: hatchling.

---

## 3. الواجهات الخارجية (بلا أسرار)

### 3.1 OANDA v20 REST — المصدر الحي الوحيد للسعر

الصنف: `nanobot/trading/oanda.py`. لا WebSocket لأسعار الذهب.

| العنصر | القيمة |
|---|---|
| الأداة | `XAU_USD` (`OANDA_INSTRUMENT`)؛ الرمز الداخلي `XAUUSD` (`DATA_SYMBOL`) |
| المصادقة | رأس `Authorization: Bearer {OANDA_API_TOKEN}` و`Content-Type: application/json` |
| الشموع | `GET {base}/v3/instruments/XAU_USD/candles` |
| السعر | `GET {base}/v3/accounts/{OANDA_ACCOUNT_ID}/pricing?instruments=XAU_USD` |
| مهلة الشموع | `httpx.Client(timeout=20.0)` |
| مهلة السعر | `httpx.Client(timeout=15.0)` |
| `price` | `M` (منتصف) |
| سقف `count` | `min(max(1, count), 5000)` |
| نطاق التاريخ | `HISTORY_LOOKBACK_MS` = عشر سنوات مدنية تقريباً |

جدول `GRANULARITY`:

| فاصل المنتج | OANDA |
|---|---|
| `1m` | `M1` |
| `3m` | `M3` |
| `5m` | `M5` |
| `15m` | `M15` |
| `30m` | `M30` |
| `1h` | `H1` |
| `2h` | `H2` |
| `4h` | `H4` |
| `6h` | `H6` |
| `8h` | `H8` |
| `12h` | `H12` |
| `1d` | `D` |
| `1w` | `W` |
| `1M` | `M` |

`BAR_DURATION_MS` معرّف لـ `1m` و`3m` و`5m` و`15m` و`30m` و`1h` و`2h` و`4h` و`1d` و`1w` فقط؛ غير ذلك يسقط إلى `60000`.

أنماط الاستعلام:

| الشرط | سلسلة الاستعلام |
|---|---|
| `from_ms` و`to_ms` و`to_ms > from_ms` | `granularity` + `from` ISO-Z + `to` ISO-Z + `price=M`؛ `to` يُقصّ إلى الآن ناقص ثانية؛ `from` لا أقدم من `to - 4800 * bar_ms` |
| `before_ms > 0` | `granularity` + `count` + `to` ISO-Z + `price=M` |
| غير ذلك | `granularity` + `count` + `price=M` |

الاستجابة تُحوَّل إلى `OandaCandle(time_ms, open, high, low, close, volume, complete)` من `mid.o/h/l/c`. `OandaQuote` يحسب `mid` من أول bid/ask. `tradeable` يكون `False` فقط إذا أرسلت OANDA `tradeable` صراحةً `false`.

لا أوامر وساطة. لا حسابات تداول تُفتح من هذا المنتج.

### 3.2 Forex Factory

| العنصر | القيمة |
|---|---|
| الملف | `nanobot/trading/news/forex_factory.py` |
| العنوان | `https://nfs.faireconomy.media/ff_calendar_thisweek.json` |
| النقل | `urllib.request.urlopen` مهلة 8 ثوانٍ |
| الشرط | `FOREX_FACTORY_ENABLED` في `{1, true, yes}` |
| العملات | `USD` أو `XAU` أو `ALL` أو أي `country`/`currency` يحتوي `USD` |
| الأثر | `high` أو `medium` أو `red` أو `orange` |
| الحد | 12 حدثاً |
| الحقول المُخرَجة | `title`، `currency`، `impact`، `time` |
| الفشل | أي استثناء → قائمة فارغة |

### 3.3 نماذج اللغة

المسار الحي يمر بـ `config.json` → `Config.get_provider` → عميل المزود. قالب Render يفترض Anthropic. الإنتاج على VPS يستخدم ما كُتب أثناء `onboard` أو عُدّل لاحقاً في WebUI. الـ synthesizer يستدعي `complete` بدرجة حرارة `0.2` كما وُثّق في المرحلة 4.

لا عنوان LLM ثابت في شفرة التداول. العناوين الافتراضية لكل مزوّد تأتي من سجل `nanobot/providers/registry.py` عندما يكون `api_base` فارغاً.

### 3.4 بحث الويب (أداة `web`؛ اختيارية)

| المزود | العنوان في `nanobot/agent/tools/web.py` | اسم المفتاح |
|---|---|---|
| Brave | `https://api.search.brave.com/res/v1/web/search` | `BRAVE_API_KEY` |
| Tavily | `https://api.tavily.com/search` | `TAVILY_API_KEY` |
| Jina search | `https://s.jina.ai/{query}` | `JINA_API_KEY` |
| Jina reader | `https://r.jina.ai/{url}` | `JINA_API_KEY` |
| Kagi | `https://kagi.com/api/v1/search` | `KAGI_API_KEY` |
| Exa | `https://api.exa.ai/search` | `EXA_API_KEY` |
| Serper | `https://google.serper.dev/search` | `SERPER_API_KEY` |
| Bocha | `https://api.bochaai.com/v1/web-search` | `BOCHA_API_KEY` |
| KeenEnable | `https://api.keenable.ai/v1/search` | `KEENABLE_API_KEY` |
| AnySearch | `https://api.anysearch.com/v1/search` | `ANYSEARCH_API_KEY` |
| VolcEngine | `https://open.feedcoopapi.com/search_api/web_search` | `VOLCENGINE_SEARCH_API_KEY` أو `WEB_SEARCH_API_KEY` |
| SearXNG | `{SEARXNG_BASE_URL}` | لا مفتاح؛ يحتاج عنواناً |
| Olostep | SDK `olostep.AsyncOlostep` | `OLOSTEP_API_KEY` |
| DuckDuckGo | حزمة `ddgs` بلا مفتاح | لا يوجد |

### 3.5 قنوات الرسائل

| القناة | الشبكة | الاعتماد |
|---|---|---|
| Telegram | Bot API عبر `python-telegram-bot` (polling أو webhook HTTPS) | extra غير موجود في `pyproject.toml`؛ يُثبَّت في سكربت النشر |
| WhatsApp | بروتوكول neonize + `neonize.db` | يُثبَّت كقناة Docker الافتراضية |
| WebUI | WebSocket على منفذ القناة + HTTP لنفس العملية | مضمّن |

### 3.6 خدمات اختيارية أخرى

| الخدمة | الدور |
|---|---|
| Langfuse | مراقبة إن وُجدت `LANGFUSE_SECRET_KEY` و`LANGFUSE_PUBLIC_KEY` |
| AWS Bedrock | إن اُختير مزود `bedrock` |
| AssemblyAI / Groq / OpenAI / OpenRouter / MIMO / StepFun / SiliconFlow | نسخ صوت |
| Render | استضافة Docker بديلة عن VPS؛ `autoDeploy: false`، قرص 1 GB على `/home/nanobot/.nanobot`، `healthCheckPath: /` |
| certbot | TLS لـ `NANOAGENT_DOMAIN` على VPS |
| nginx | وكيل إلى `127.0.0.1:8766` مع ترقية WebSocket و`proxy_read_timeout 3600s` |

لا Postgres. لا Redis. لا وسيط رسائل خارجي.

---

## 4. HTTP الداخلي للتداول

المسار: `nanobot/webui/trading_api.py` → `dispatch_trading_route`. تُخدم من عملية البوابة/WebSocket وليس من `nanobot serve` (ذلك خادم OpenAI-compatible على 8900).

| المسار | المعالج | الاستعلام | الاستجابة |
|---|---|---|---|
| `/api/trading/klines` | `handle_trading_klines` | `symbol` (يُقسر إلى ذهب)، `interval` افتراضي `1h`، `limit` افتراضي `300`، `before`، `from`، `to` | `{symbol, interval, source:"oanda", candles, hasMore, pending}` أو خطأ إعداد/502 |
| `/api/trading/quote` | `handle_trading_quote` | `symbol` | `{symbol, configured, quote:{bid,ask,mid,tradeable}}` |
| `/api/trading/status` | `handle_trading_status` | لا | `{symbol, oanda_configured, oanda_env, runtime}` |
| `/api/trading/runtime/update` | `handle_trading_runtime_update` | أي من `paused`، `kill_switch`، `paper_mode` كـ `1/true/yes/on` | `{runtime}` أو 400 إن لم يُمرَّر حقل |
| `/api/trading/analyze` | `handle_trading_analyze` | `interval` افتراضي `15m`، `team_mode` افتراضي `core`، `preset` | `result_to_wire`؛ `debate` يستدعي `run_debate_crew`؛ `swarm`+`preset` يستدعي `run_swarm`؛ غير ذلك `run_unified_chart_agent` |
| `/api/trading/recommendations` | `handle_trading_recommendations` | لا | `{recommendations: list_recommendations()}` |
| `/api/trading/briefing` | `handle_trading_briefing` | لا | سعر + آخر توصية مفتوحة + آخر 5 + `summary` |
| `/api/trading/performance` | `handle_trading_performance` | لا | عدّادات اتجاه وحالة + `paperActions` + آخر قرارات |
| `/api/trading/paper` | `handle_trading_paper` | `recommendation_id` إلزامي، `action` افتراضي `approve` | `{ok, entry}` |

`handle_trading_performance` يعدّ `status == "open"` مفتوحاً. صفوف المخزن تُكتب عادةً بـ `valid_now` أو `awaiting_activation` كما في المرحلة 4؛ عمود `open` قد يبقى صفراً إن لم تُرحَّل الحالات. يُعاد ذكر هذا في المرحلة 6.

---

## 5. مخططات التخزين

كل المسارات نسبةً إلى `get_data_dir()` ما لم يُذكر غير ذلك.

### 5.1 SQLite `trading/recommendations.db`

الملف: `nanobot/trading/recommendations/store.py`. يُنشأ المجلد عند أول اتصال. إن غاب عمود `session_key` يُنفَّذ `ALTER TABLE recommendations ADD COLUMN session_key TEXT`.

```sql
CREATE TABLE IF NOT EXISTS recommendations (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry REAL,
    stop_loss REAL,
    targets_json TEXT,
    status TEXT NOT NULL,
    summary TEXT,
    confidence REAL,
    drawings_json TEXT,
    gate_json TEXT,
    created_at INTEGER NOT NULL,
    session_key TEXT
);
```

| العمود | المعنى عند الكتابة |
|---|---|
| `id` | `uuid4` نصاً |
| `symbol` | `rec.symbol` (ذهب) |
| `interval` | `rec.interval` |
| `direction` | `rec.action` (`buy` أو `sell`) |
| `entry` | رقم |
| `stop_loss` | رقم |
| `targets_json` | `json.dumps(rec.targets)` قائمة أرقام |
| `status` | `rec.execution_state` أو `"valid_now"` |
| `summary` | `decision.summary` |
| `confidence` | `decision.confidence` |
| `drawings_json` | قائمة `{type, label, color, points, meta}` |
| `gate_json` | قائمة `{id, status, reason_ar}` من `gate_chain.verdicts` أو `NULL` |
| `created_at` | Unix ms |
| `session_key` | مفتاح المحادثة أو `NULL` |

`store_recommendation` يرفض الكتابة إذا: الخطة غير قابلة للتداول، أو ينقص entry/SL/أهداف، أو يوجد صف حي لنفس `session_key` بحالة `valid_now` أو `awaiting_activation`. النجاح يستدعي أيضاً `record_trade_decision`.

القراءات: `get_recommendation` و`latest_live_recommendation` و`list_recommendations(limit=20)` لا تُعيد `drawings_json` ولا `gate_json` في SELECT.

لا فهارس إضافية غير PRIMARY KEY.

### 5.2 SQLite `llm_usage.sqlite3`

الملف: `nanobot/llm_usage/store.py`. WAL، `synchronous=NORMAL`، `temp_store=MEMORY`.

```sql
CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY,
    started_at_ms INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    source TEXT NOT NULL,
    stream INTEGER NOT NULL,
    finish_reason TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cache_read_tokens INTEGER,
    cache_write_tokens INTEGER,
    reported_tokens INTEGER,
    estimated_tokens INTEGER,
    generation_ms INTEGER,
    measured_output_tokens INTEGER,
    ttft_ms INTEGER,
    timed_requests INTEGER,
    error_status_code INTEGER,
    error_kind TEXT
);
CREATE INDEX IF NOT EXISTS llm_calls_started_at_idx
    ON llm_calls(started_at_ms);
CREATE INDEX IF NOT EXISTS llm_calls_provider_model_time_idx
    ON llm_calls(provider, model, started_at_ms);
```

المسار: `get_data_dir() / "llm_usage.sqlite3"`. لا يُخزَّن نص المحادثة.

### 5.3 JSONL `trading/trades.jsonl`

يكتبه `nanobot/trading/memory/decisions.py` سطراً واحداً لكل توصية مخزّنة:

| المفتاح | النوع |
|---|---|
| `id` | نص معرّف التوصية |
| `ts` | Unix ms |
| `symbol` | نص؛ افتراضي `XAUUSD` |
| `interval` | نص؛ افتراضي `15m` |
| `direction` | `decision.decision` |
| `confidence` | رقم |
| `summary` | نص |
| `entry` | رقم أو فارغ |
| `stop_loss` | رقم أو فارغ |
| `targets` | قائمة |
| `execution_state` | نص |
| `quote_mid` | رقم أو فارغ |
| `key_reasons` | حتى 5 عناصر |
| `risk_warnings` | حتى 5 عناصر |

`format_decisions_for_dream` يقرأ آخر 10 أسطر لدمج Dream.

### 5.4 JSONL `trading/paper_ledger.jsonl`

يكتبه `nanobot/trading/paper.py`:

| المفتاح | النوع |
|---|---|
| `id` | `uuid4` |
| `recommendation_id` | نص |
| `action` | نص (من الاستعلام؛ الافتراضي `approve`) |
| `note` | نص؛ افتراضي فارغ |
| `ts` | Unix ms |

### 5.5 JSON `trading/runtime_state.json`

يكتبه `nanobot/trading/runtime_state.py`:

```json
{
  "paused": false,
  "kill_switch": false,
  "paper_mode": true
}
```

الافتراضي في الذاكرة إن غاب الملف: `paused=False`، `kill_switch=False`، `paper_mode=True`. التحديث عبر `/api/trading/runtime/update` أو `TradingRuntimeStore.update`.

### 5.6 جلسات JSONL

| المسار | الدور |
|---|---|
| `{data_dir}/sessions/{base64url(session_key)}.jsonl` | المخزن الحالي؛ `JsonlSessionStore.get_session_path` |
| `{data_dir}/sessions/{base64url(session_key)}.runtime-checkpoint` | لاحقة نقطة تحقق وقت التشغيل ثم تُحذف بعد الحفظ الذري |
| `{data_dir}/sessions/{safe_filename(key)}.jsonl` | اسم تراثي |
| `~/.nanobot/sessions/{safe_key}.jsonl` | تراث عالمي عبر `get_legacy_sessions_dir()` |

سطر metadata الأول:

```json
{
  "_type": "metadata",
  "key": "channel:chat_id",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "metadata": {},
  "last_archived": 0,
  "last_consolidated": 0
}
```

سطر حالة المزود الاختياري: `{"_type": "provider_state", "state": <ناتج ProviderConversationState.to_private_record()>}` حيث الثابت `_PROVIDER_STATE_RECORD_TYPE = "provider_state"` في `nanobot/session/manager.py`. باقي الأسطر رسائل: `role`، `content`، `timestamp`، وقد توجد `tool_calls` و`tool_call_id` و`name` و`reasoning_content` و`thinking_blocks` و`media` و`cli_apps`.

`SessionInfo` للقوائم: `key`، `created_at`، `updated_at`، `title`، `preview`، `path`.

### 5.7 WebUI transcripts

`get_webui_dir()` = `{data_dir}/webui`. ملفات `{stem}.jsonl` وقطاعات `\d{6}.jsonl` تحت مجلد القطاعات. الفهرس في `nanobot/webui/session_list_index.py`.

### 5.8 ذاكرة مساحة العمل (ملفات وليست SQL)

تحت `agents.defaults.workspace` (افتراضي `~/.nanobot/workspace`؛ على VPS يتبع `HOME`):

| المسار | الدور |
|---|---|
| `memory/MEMORY.md` | ذاكرة طويلة |
| `memory/history.jsonl` | تاريخ Dream؛ ترحيل من `HISTORY.md` إن وُجد |
| `memory/SOUL.md` | هوية الوكيل |
| `memory/USER.md` | ملف المستخدم |
| `cron/jobs.json` | مخزن cron الحالي (`workspace_path / "cron" / "jobs.json"`) |
| `{data_dir}/cron/jobs.json` | تراث؛ يُنقل مرة واحدة عبر `_migrate_cron_store` |

`CronStore.version` افتراضي `1`. كل `CronJob`:

| الحقل | المعنى |
|---|---|
| `id` | نص |
| `name` | نص |
| `enabled` | منطقي |
| `schedule.kind` | `at` أو `every` أو `cron` |
| `schedule.at_ms` | للطابع |
| `schedule.every_ms` | للفاصل |
| `schedule.expr` | تعبير cron |
| `schedule.tz` | منطقة زمنية |
| `payload.kind` | `system_event` أو `agent_turn` |
| `payload.message` | نص |
| `payload.deliver` | تراث |
| `payload.channel` | تراث |
| `payload.to` | تراث |
| `payload.channel_meta` | كائن |
| `payload.session_key` | ربط الجلسة |
| `payload.origin_channel` | أصل |
| `payload.origin_chat_id` | أصل |
| `payload.origin_metadata` | أصل |
| `state.next_run_at_ms` | رقم أو null |
| `state.last_run_at_ms` | رقم أو null |
| `state.last_status` | `ok` أو `error` أو `skipped` |
| `state.last_error` | نص |
| `state.run_history` | حتى 20 سجل `{run_at_ms, status, duration_ms, error}` |
| `created_at_ms` | رقم |
| `updated_at_ms` | رقم |
| `delete_after_run` | منطقي |

ملفات مجاورة: `{cron}/action.jsonl` و`{cron}/runs/` وملف قفل `{cron}.lock`. وظائف `agent_turn` بلا سياق جلسة تُعطَّل.

### 5.9 مسارات تشغيل أخرى

| المسار | الدور |
|---|---|
| `{data_dir}/whatsapp-auth/neonize.db` | جلسة WhatsApp (+ `-wal` و`-shm` محتملة) |
| `{data_dir}/media/{channel}/` | وسائط القنوات |
| `{data_dir}/logs/` | سجلات |
| `~/.nanobot/history/cli_history` | تاريخ CLI المشترك |
| مساحة عمل Docker API | `/home/nanobot/.nanobot/api-workspace` في `docker-compose.yml` |

---

## 6. التشغيل والتثبيت

### 6.1 متطلبات محلية

| المكوّن | القيمة |
|---|---|
| بايثون | `>=3.11` (`install.sh` يرفض أقدم) |
| الحزمة | `nanobot-ai` من PyPI أو `pip install -e .` / `uv sync` من المستودع |
| Node/Bun لواجهة التطوير | WebUI: Bun 1.3.6 في CI أو npm في Docker Node 24؛ TUI: Bun 1.3.13 |
| قنوات هذا المنتج | Telegram وWhatsApp extras تُثبَّت يدوياً أو عبر `scripts/install_channel_dependencies.py` |

### 6.2 أوامر CLI (`nanobot` → `nanobot.cli.entry:main`)

| الأمر | الملف | الوظيفة |
|---|---|---|
| `nanobot` / `nanobot --help` | `nanobot/cli/commands.py` | جذر Typer |
| `nanobot onboard` | نفس الملف | ينشئ/يحدّث `config.json` ومساحة العمل؛ `--wizard` تفاعلي؛ `--refresh` بلا أسئلة؛ `--workspace`؛ `--config` |
| `nanobot trigger TRIGGER_ID [MESSAGE]` | نفس الملف | يصفّر رسالة في `LocalTriggerStore` |
| `nanobot serve` | نفس الملف | خادم OpenAI-compatible `/v1/chat/completions`؛ extra `api`؛ افتراضي `127.0.0.1:8900` |
| `nanobot webui` | `nanobot/cli/webui.py` | يطلق/يربط WebUI وقد يبدأ بوابة |
| `nanobot gateway` | `nanobot/cli/gateway.py` | يبدأ البوابة؛ `--foreground` أو `--background`؛ `--port`؛ `--workspace`؛ `--config` |
| `nanobot gateway status` | نفس الملف | حالة العملية |
| `nanobot gateway logs` | نفس الملف | سجلات |
| `nanobot gateway stop` | نفس الملف | إيقاف |
| `nanobot gateway restart` | نفس الملف | إعادة تشغيل |
| `nanobot gateway install-service` | نفس الملف | تثبيت خدمة نظام عامة |
| `nanobot gateway uninstall-service` | نفس الملف | إزالة الخدمة |
| `nanobot agent` | `nanobot/cli/agent.py` | دورة وكيل تفاعلية في الطرفية |
| `nanobot sessions restore-workspace` | `nanobot/cli/commands.py` | استعادة جلسات إلى مساحة العمل |
| `nanobot channels status` | نفس الملف | حالة القنوات |
| `nanobot channels login` | نفس الملف | تسجيل دخول قناة (مثل QR لواتساب) |
| `nanobot plugins list` | نفس الملف | extras |
| `nanobot plugins enable NAME` | نفس الملف | تثبيت extra |
| `nanobot plugins disable NAME` | نفس الملف | إزالة extra |
| `nanobot status` | نفس الملف | ملخص الإعداد والمزوّد |
| `nanobot provider login` | `nanobot/cli/provider.py` | تسجيل OAuth لمزوّد (`openai_codex` أو `xai_grok` أو `github_copilot`) |
| `nanobot provider logout` | `nanobot/cli/provider.py` | إلغاء جلسة OAuth لنفس المزوّدين |
| `nanobot-desktop-tui` | `nanobot/cli/desktop_tui.py` | ثنائي سطح المكتب |

إنتاج هذا المنتج:

```
nanobot gateway --foreground --port 18791
```

وحدة systemd `nanoagent-gateway.service`:

```
[Unit]
Description=NanoAgent Gold Trading Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=nanoagent
WorkingDirectory=/opt/nanoagent
Environment=PATH=/opt/nanoagent/.venv/bin:/usr/bin:/bin
Environment=HOME=/opt/nanoagent
EnvironmentFile=-/opt/nanoagent/.env
ExecStart=/opt/nanoagent/.venv/bin/nanobot gateway --foreground --port 18791
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

الحي: `https://nanoagent.lork.cloud/` عبر nginx إلى `127.0.0.1:8766`. صحة البوابة على `18791`. لا تُلمس `/opt/foxagent`.

### 6.3 تثبيت من السكربت

`scripts/install.sh` (و`install.ps1`): يثبّت `nanobot-ai` من PyPI في venv أو عبر `uv tool install` ثم `nanobot onboard --wizard` ما لم يكن `NANOBOT_SKIP_WIZARD=1`. من المستودع: `python -m pip install -e .` أو `uv sync`. بناء WebUI للمطوّر: `cd webui && bun install && bun run build` (VPS يستخدم Bun بعد تثبيته إن غاب).

---

## 7. Docker

### 7.1 `Dockerfile`

مرحلتان:

1. `node:24-bookworm-slim` كـ `webui-builder`: `npm ci` في `webui/` ثم `npm run build` إلى `/app/nanobot/web/dist`.
2. `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`: يثبّت `ca-certificates git bubblewrap openssh-client libmagic1`، ينشئ `/app/.venv`، يثبّت العجلة مع `NANOBOT_SKIP_WEBUI_BUILD=1`، ينسخ المصدر و`render-config.json`، يثبّت قنوات `NANOBOT_CHANNELS`، ينشئ مستخدم `nanobot` uid `1000`، `ENTRYPOINT entrypoint.sh`، `CMD ["status"]`.

منافذ الصورة: `18790` و`8765`.

### 7.2 `entrypoint.sh`

1. إن `RENDER=true`: أنشئ `$HOME/.nanobot` وانسخ القالب إلى `config.json` إن غاب ثم ألحق `--config`.
2. إن uid=0: `chown` دليل البيانات ثم `setpriv --reuid=nanobot --regid=nanobot --init-groups nanobot "$@"`؛ الفشل يخرج 1 ولا يشغّل الوكيل كجذر.
3. إن غير جذر ودليل البيانات غير قابل للكتابة: رسالة تطلب `chown 1000:1000` ثم خروج 1.
4. غير ذلك: `exec nanobot "$@"`.

### 7.3 `docker-compose.yml`

خدمات تشترك في بناء الصورة و`--cap-drop ALL` و`--cap-add CHOWN,SETGID,SETUID` و`no-new-privileges:true` وربط `~/.nanobot` إلى `/home/nanobot/.nanobot`.

| الخدمة | الأمر | المنافذ | الحدود |
|---|---|---|---|
| `nanobot-gateway` | `gateway` | `127.0.0.1:18790:18790` و`8765:8765` | 1 CPU / 1G؛ حجز 0.25 / 256M |
| `nanobot-api` | `serve --host 0.0.0.0 -w /home/nanobot/.nanobot/api-workspace` | `127.0.0.1:8900:8900` | نفس الحدود |
| `nanobot-cli` | `status` (ملف `cli`) | لا نشر | نفس الحدود؛ TTY |

`NANOBOT_CHANNELS` الافتراضي في compose: `whatsapp`.

### 7.4 `docker-compose.bwrap.yml`

يضيف `SYS_ADMIN` و`apparmor=unconfined` و`seccomp=unconfined` للخدمات الثلاث من أجل bubblewrap.

### 7.5 `render.yaml`

خدمة ويب Docker اسمها `nanobot`، `dockerCommand: gateway`، `autoDeploy: false`، خطة `starter`، قرص `nanobot-data` 1 GB على `/home/nanobot/.nanobot`. متغيرات: `ANTHROPIC_API_KEY` (sync false)، `NANOBOT_WEB_TOKEN` (sync false)، `PORT=8765`.

---

## 8. CI

مسار التجاهل على مستوى الحدث في `.github/workflows/ci.yml`: `docs/**`، `.agent/**`، `.github/ISSUE_TEMPLATE/**`، `AGENTS.md`، `CLAUDE.md`، `COMMUNICATION.md`، `CONTRIBUTING.md`، `README.md`، `SECURITY.md`، `webui/README.md`. لذلك هذا الفرع التوثيقي لا يشغّل معظم CI على PR إلى `main`.

### 8.1 وظيفة `changes`

تقارن نطاق git ثلاثي النقاط بين `BASE_SHA` و`HEAD_SHA` على `pull_request`، أو نطاق النقطتين بين `BASE_SHA` و`HEAD_SHA` على `push`، ثم تعيّن:

| العلم | يُفعَّل عند |
|---|---|
| `python_required` | `nanobot/*` (ما عدا WebUI القنوات الذي يُحسب webui)، `tests/*`، `conftest.py`، `uv.lock`، `scripts/*`، `pyproject.toml`، `hatch_build.py`، `scripts/install_channel_dependencies.py`، تغيير workflow، أو مسار غير مصنّف |
| `webui_required` | `webui/*` أو `nanobot/channels/*/webui/*` أو workflow أو غير مصنّف |
| `tui_required` | `tui/*` أو workflow أو غير مصنّف |
| `docker_required` | `nanobot/*`، `webui/*`، `Dockerfile`، `Dockerfile.*`، `.dockerignore`، `docker-compose*.yml`، `entrypoint.sh`، `render-config.json`، `README.md`، `LICENSE`، `THIRD_PARTY_NOTICES.md`، `tests/test_docker.sh`، `pyproject.toml`، `hatch_build.py`، `scripts/install_channel_dependencies.py`، workflow أو غير مصنّف |

`docs/*` و`render.yaml` لا يفعّلان أي علم بعد أن يتجاوز الحدث `paths-ignore`.

### 8.2 وظيفة `test` (بايثون)

مصفوفة:

| الاسم | نظام | بايثون | تغطية | pytest |
|---|---|---|---|---|
| minimum, 3.11 | ubuntu-latest | 3.11 | لا | `-n auto --dist loadfile --ignore=tests/cli/test_commands.py` ثم اختبارات CLI تسلسلياً |
| latest, 3.14 + coverage | ubuntu-latest | 3.14 | نعم؛ `ruff check nanobot tests conftest.py` و`basedpyright` و`--cov=nanobot` مع `fail_under = 75` في `pyproject.toml` | نفس التجاهل ثم CLI مع `--cov-append` |
| Windows, 3.14 | windows-latest | 3.14 | لا | يتجاهل أيضاً `tests/tools/test_exec_platform.py` |

خطوات مشتركة: `actions/checkout@v4`، `actions/setup-python@v5`، `astral-sh/setup-uv@v4`، على Linux `libolm-dev build-essential`، `uv sync --all-extras --dev`، `python -m scripts.install_channel_dependencies --all-channels`، `uv pip check`. المهلة 20 دقيقة. `fail-fast: false`.

وظيفة منفصلة `windows_process` تشغّل فقط `tests/tools/test_exec_platform.py` على Windows 3.14.

### 8.3 وظيفة `webui`

ubuntu، Bun 1.3.6، داخل `webui/`: `npm ci --ignore-scripts --dry-run`، `bun install --frozen-lockfile`، `bun run lint`، `bun run test:coverage`، `bun run build`. مهلة 15 دقيقة.

### 8.4 وظيفة `tui`

مصفوفة ubuntu وwindows. Bun 1.3.13 داخل `tui/`: `bun install --frozen-lockfile`، `bun run check`، `bun run test`، `python3 scripts/pty_smoke.py` على Linux، وعلى Windows `pywinpty==3.0.5` ثم `python scripts/conpty_smoke.py`، `bun run build`، ثم `bun scripts/release-notices.ts` و`package-release.py` للهدف (`linux-x64` أو `win32-x64`). مهلة 10 دقائق.

### 8.5 وظيفة `docker`

`docker build -t nanobot:test .` ثم `docker compose run --rm --no-deps --build -T nanobot-cli status` ثم فحص أن الحاوية تبدأ كجذر مع `NoNewPrivs=1` وأن `setpriv` يصل إلى uid 1000 بلا قدرات، ثم التحقق من أن overlay `docker-compose.bwrap.yml` يضيف `SYS_ADMIN` مع القدرات الثلاث و`no-new-privileges:true`. بعد ذلك `import neonize, segno` والتحقق أن uid 1000 يكتب `/app/.venv` ولا يكتب `/app` ولا `/app/nanobot`، وتجربة تثبيت قناة `discord` داخل الصورة. مهلة 20 دقيقة.

### 8.6 `.github/workflows/tui-release.yml`

يدوي `workflow_dispatch` يتطلّب `tag` يطابق `vMAJOR.MINOR.PATCH` مع لاحقة اختيارية و`compliance_reviewed=true`. يبني على ubuntu أهداف `darwin-arm64` و`darwin-x64` و`linux-arm64` و`linux-x64` و`win32-x64`، يوقّع macOS ad-hoc عبر `indygreg/apple-code-sign-action`، ويرفع `tui/dist/nanobot-tui-${TARGET}.zip` و`.sha256` إلى إصدار GitHub الموجود. صلاحية `contents: write`. ليس مسار نشر الذهب.

قوالب القضايا فقط: `.github/ISSUE_TEMPLATE/bug_report.yml` و`feature_request.yml` و`config.yml`.

---

## 9. ملخص مسار البيانات للإعداد

1. المشغّل يضع أسماء `OANDA_*` في `/opt/nanoagent/.env` (أو بيئة الحاوية) ويفعّل اختيارياً `FOREX_FACTORY_ENABLED`.
2. systemd أو `entrypoint.sh` يطلق `nanobot gateway` مع `HOME` الذي يجعل `get_config_path()` يشير إلى `{HOME}/.nanobot/config.json`.
3. المحمّل يحلّ `${VAR}` ويدمج تجاوزات `NANOBOT_*__*`.
4. `load_trading_config()` يقرأ `OANDA_*` من `os.environ` في كل طلب سوق.
5. الشموع تُجلب من OANDA REST؛ الأخبار من Forex Factory فقط إن فُعّلت؛ القرار من LLM حسب `providers`؛ التوصية تُكتب في `recommendations.db` و`trades.jsonl`؛ الحالة التشغيلية في `runtime_state.json`؛ الورق في `paper_ledger.jsonl`.
6. WebUI على منفذ القناة يقرأ `/api/trading/*` من العملية نفسها.

---

## 10. جاهزية المرحلة التالية

المرحلة 6 تبدأ من: نقاط القوة والضعف لهذا المنتج بعد قصّ أدوات الترميز؛ جرد الكود الميت (`stage_checkpoint.py`، `explain_stored_recommendation`، استيراد `AnalyzeGoldTool` غير المستخدم، مرشّح منطقة الطلب الذي لا يعمل، `daily_bias` المحسوب من 1h، حقول `performance` التي تعدّ `open`، مهارات README القديمة)؛ مسح `TODO`/`FIXME`/`XXX`/`HACK`؛ مراجعة أمنية لأسماء الأسرار وwebhook وtoken وSSRF و`webuiAllowRemotePackageInstall` على VPS؛ الدين التقني؛ عشرة اقتراحات تحسين مرتّبة؛ خارطة طريق قصيرة دون تقدير بالأيام.
