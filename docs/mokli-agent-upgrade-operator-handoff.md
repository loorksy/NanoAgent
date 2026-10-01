# تسليم ترقية Mokli — للمشغّل (بعد Cloud Agent)

## قائمة إغلاق الإنتاج (§11)

1. نشر الفرع على VPS: `bash scripts/vps_pull_main.sh cursor/section11-vps-rows-d9e1` (`PULL_OK` بعد `:18791` + Agent API `:8766`؛ يُصلح ملكية `section11-events/`). **لا** تشغّل `vps_pull_main.sh` بدون فرع قبل دمج PR — الافتراضي `main` يزيل سكربتات §11؛ `vps_section11_env_check.sh` يطبع `git_branch=` وHINT إن كان الفرع خاطئاً. عند خطأ Permission denied قديم: `bash scripts/vps_section11_fix_events_ownership.sh`
2. OpenRouter credits + `OANDA_*`: `bash scripts/vps_section11_set_oanda_env.sh` (optional paid model on **this shell** before row scripts: `export MOKLI_SECTION11_MODEL=openai/gpt-4o-mini` — forwarded over SSH; see `docs/section11-vps-env.example`)
3. جاهزية: `bash scripts/vps_section11_quota_status.sh` (cached؛ بلا نداء LLM؛ عند 429 يطبع **≈وقت إعادة تعيين OpenRouter** من `X-RateLimit-Reset` في `quota-probe.jsonl`) ثم `bash scripts/vps_section11_env_check.sh --require-quota --require-oanda` (exit 0؛ يطبع أيضاً `mokli_ui_http` و`mokli_pipe_show_diagnostics` لصف 12). أو دفعة واحدة (probe حي + env + blockers @13): `bash scripts/mokli_upgrade_section11_operator_unblock.sh` (exit 0 = جاهز لـ `close.sh --apply`). مع سحب الفرع أولاً: `bash scripts/mokli_upgrade_section11_operator_unblock.sh --pull-vps`. عند quota محجوب: `bash scripts/mokli_upgrade_section11_operator_unblock.sh --skip-probe` (بلا نداء LLM إضافي)
4. إعادة الصفوف الجزئية + P0: `bash scripts/mokli_upgrade_section11_rerun_partials.sh` — أو بعد reset OpenRouter: `bash scripts/mokli_upgrade_section11_after_reset_wake.sh` (= pull + probe + reruns؛ **بدون** انتظار طويل). **سلسلة كاملة (مؤقت Cloud Agent):** `bash scripts/mokli_upgrade_section11_timer_wake.sh --wait-quota` (ينتظر reset إن لزم؛ أثناء الحجب: `--dry-run` بلا LLM). بديل: `bash scripts/mokli_upgrade_section11_post_quota.sh --wait --pull-vps`
5. صفوف 11–13 (UI/جهاز): `bash scripts/mokli_upgrade_section11_remaining_rows.sh`
6. املأ `section11-results.json`؛ `bash scripts/mokli_upgrade_section11_sync_from_vps.sh --pull-vps` (يكتب `section11-events/p0-interim-summary.txt` + **P0 local estimate** `--compare` بلا LLM)
7. بوابة: بعد خطوة 6 استخدم `bash scripts/mokli_upgrade_section11_blockers.sh` (exit 0). أو دفعة واحدة (سحب + env + artifacts): `bash scripts/mokli_upgrade_section11_production_gate.sh --pull-vps`
   - تحقق محلي للصفوف 1–10 فقط: `bash scripts/mokli_upgrade_section11_blockers.sh --skip-vps --require-through 10` (يسمح بـ PARTIAL في JSON)
   - إغلاق 1–13: validate يرفض PARTIAL ويتطلب `01-no-tools-after-p0.jsonl` عند `--require-through 13` (معاينة: `close.sh --allow-partial` بدون `--apply`)
   - معاينة جدول §11 للصفوف 1–10: `bash scripts/mokli_upgrade_section11_close.sh --results section11-results-partial.json --require-through 10` (بدون `--apply`)
8. تحديث التقرير: `bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13` (صف 9: عمود «الأرقام» يضم `session-summary` تلقائياً عند تعدد diagnostics في JSONL؛ يحدّث أيضاً جدول §2.1 وفقرة **P0 live delta** عند وجود `01-no-tools-after-p0.jsonl` مع `in>0`)
9. `pytest tests/scripts/test_mokli_upgrade_report_section11_gate.py -q`؛ اختياري قبل الدمج: `bash scripts/mokli_upgrade_aggregate_pytest.sh`

## الفرع

- **الإنتاج:** `main` (دمج PR ترقية الوكيل + تغذية OANDA/MetaAPI — راجع `git log -1` على `origin/main`)
- فرع التطوير السابق: `cursor/agent-runtime-efficiency-d9e1` → دُمج في `cursor/broker-market-feed-d9e1` ثم `main`

### أسرار Cloud Agent (نشر من الوكيل)

```bash
bash scripts/cloud_agent_vps_secrets_check.sh
```

- المطلوب في البيئة: **`VPS`** (أو `user@host`) و **`VPSPASS`**. الأسماء `vps` / `password` تُعرَض إلى `VPS` / `VPSPASS` عبر `scripts/vps_env.sh`.
- إذا ظهر `CLOUD_AGENT_INJECTED_SECRET_NAMES=password,vps` لكن الفحص يفشل، الأسرار **مسجّلة ولم تُحقَن** في shell هذا التشغيل — احفظها باسم `VPS`/`VPSPASS` و**ابدأ تشغيل وكيل جديد**، أو صدّرها يدوياً قبل `deploy-mokli-vps.sh`.

### نشر سريع بعد الدمج

**مفتاح SSH (بدون VPS/VPSPASS):** إذا كان `~/.ssh/config` يعرّف المضيف (مثلاً `hostinger-vps`):

```bash
export MOKLI_SSH_HOST=hostinger-vps MOKLI_INSTALL_DIR=/opt/nanoagent MOKLI_GATEWAY_SERVICE=nanoagent-gateway
bash scripts/vps_ssh.sh 'cd /opt/nanoagent && git rev-parse --short HEAD'   # one-shot remote (key auth)
bash scripts/vps_pull_main.sh   # git pull main + pip + restart (بدون nginx)
# قبل دمج PR §11: bash scripts/vps_pull_main.sh cursor/section11-vps-rows-d9e1
# (أو: MOKLI_BRANCH=cursor/section11-vps-rows-d9e1 bash scripts/vps_pull_main.sh)
bash scripts/mokli_upgrade_section11_production_gate.sh  # env + pull + status (require-through 13)
bash scripts/mokli_upgrade_section11_blockers.sh  # quota+OANDA + validate 13 (no pull); exit 0 = ready to close
bash scripts/mokli_upgrade_section11_status.sh   # exit 0 عند validate+quota OK (require-through افتراضي 13)
bash scripts/mokli_upgrade_section11_status.sh --skip-quota --require-through 10  # صفوف 1–10 فقط
bash scripts/mokli_upgrade_section11_cloud_status.sh --require-through 10  # Cloud Agent: exit 0 بعد sync إن كانت JSONL 1–10 سليمة (quota قد يبقى BLOCKED)
bash scripts/mokli_upgrade_section11_completion_status.sh --require-through 10  # cached quota + artifacts (no live LLM)
bash scripts/local_section11_row12_smoke.sh      # UI+API+pipe محلياً بلا LLM (قبل محادثة صف 12)
# أو bash scripts/deploy-mokli-vps.sh مع MOKLI_INSTALL_DIR=… عند الحاجة لمسار /opt/mokli الكامل
```

**كلمة مرور SSH:**

```bash
export VPS='user@host' VPSPASS='…' MOKLI_BRANCH=main
bash scripts/deploy-mokli-vps.sh
# أو على /opt/mokli: git fetch origin main && git checkout main && git pull --ff-only
# ثم pip install -e '.[trading-mt5]' && systemctl restart mokli-gateway
```

## ما اكتمل بدون VPS

- `docs/mokli-agent-upgrade-audit.md` — تدقيق المرحلة 0
- `docs/mokli-agent-upgrade-report.md` — §1–11.1 (جدول §11 **جزئي** من VPS؛ صفوف 11–13 + P0 after + إغلاق 13 للإنتاج)
- `docs/mokli-settings-audit.md` — P2/P3 إعدادات
- `docs/mokli-agent-upgrade-completion-audit.md` — بوابة إغلاق (ما ثبت vs §11 المعلق)
- pytest: **2425** ناجية (`bash scripts/mokli_upgrade_aggregate_pytest.sh`)
- سلسلة إغلاق §11 (بعد JSONL حي): `section11_validate` → `section11_batch` → `section11_patch_report` أو `section11_close.sh [--apply]`

## فواتير المزود (VPS)

- **Anthropic** (preset `claude-opus-5`): رصيد منخفض → صف §11 1 يفشل بلا `input_tokens`.
- **OpenRouter** (`openrouter/auto`): رفض «API key is out of quota» (2026-10-01).
- **§11 مؤقت (2026-10-01):** preset **`qwen3-8-27b-free`** على VPS — صف 1 حي: `in≈10934 out≈117 tools=0` (سياق كبير رغم سؤال قصير؛ P0 حي).
- **تجاوز نموذج الجلسة (Agent API):** `MOKLI_SECTION11_MODEL=qwen/qwen3.8-27b:free bash scripts/vps_section11_agent_api_turn.sh …` — يجب أن يكون **معرّف نموذج** ضمن سلسلة `modelPreset`/`fallbackModels` (ليس اسم preset فقط). لتشغيل Anthropic غيّر `agents.defaults.modelPreset` في config ثم أعد تشغيل البوابة.
- **حصة OpenRouter (2026-10-01):** بعد 15 دورة §11 صف 9، التشخيص صار `in=0` ورسالة `free-models-per-day` — **أوقف صفوف 9–13** حتى credits أو preset مدفوع. فحص سريع: `bash scripts/vps_section11_quota_probe.sh` (exit 1 = محجوب؛ يطبع **≈إعادة التعيين اليومية** من `X-RateLimit-Reset`). انتظار تلقائي ثم probe: `bash scripts/mokli_upgrade_section11_wait_quota_reset.sh --wait` (بعد `sync_from_vps` لـ `quota-probe.jsonl`). **سلسلة بعد عودة الحصة:** `bash scripts/mokli_upgrade_section11_post_quota.sh --wait --pull-vps` (pull + wait + probe + `rerun_partials` + sync؛ ثم `remaining_rows` و`close --apply`). **مؤقت Cloud Agent / استيقاظ طويل:** `bash scripts/mokli_upgrade_section11_timer_wake.sh --wait-quota` (ينتظر `X-RateLimit-Reset+buffer` إن كان probe محجوباً ثم `after_reset_wake` → … → `close --apply @13`). على **الخادم نفسه** (SSH إلى VPS): `cd /opt/nanoagent && bash scripts/vps_section11_quota_probe.sh` — يستخدم Agent API على `127.0.0.1:8766` بلا SSH متداخل. Cloud Agent قد يجدول متابعة تلقائية بعد ~`2026-10-02 00:00 UTC` إن بقي الحجب؛ **OANDA/credits** ما زالا يحتاجان المشغّل.
- **صف 9 (جلسة طويلة):** `MOKLI_SSH_HOST=… bash scripts/vps_section11_long_session.sh 09-long-session.jsonl 15` ثم `python scripts/mokli_upgrade_diagnostic_extract.py --file …/09-long-session.jsonl --session-summary` (يُطبع `in_last_over_first` و`below_linear_15x`).
- **سحب JSONL من VPS:** `bash scripts/mokli_upgrade_section11_sync_from_vps.sh` (pull + after_pull + validate 1–10). مع تحديث checkout: `bash scripts/mokli_upgrade_section11_sync_from_vps.sh --pull-vps`. أو يدوياً: `vps_section11_pull_events.sh` ثم `mokli_upgrade_section11_after_pull.sh` (جدول §2.1 + **P0 live delta** إذا وُجد `01-no-tools-after-p0.jsonl`).
- **صف 13 CI (بدون جهاز):** `bash scripts/mokli_upgrade_section11_row13_ci.sh` — pipe projection + `mokli-sdk`؛ لا يغني عن JSONL حي على الهاتف.
- **P0 تقدير بلا LLM:** `python scripts/mokli_upgrade_p0_turn_estimate.py --compare "مرحبا" "حلل الذهب"` — `final` / `system` / `tool_defs` / **`provider_tools`** (نفس `diagnostic.provider_tool_count`). على الدور الخفيف: chat + session tools عند التسجيل (محلي ≈3–7؛ VPS Agent API ≈7).
- **PARTIAL reruns (quota OK):** `bash scripts/mokli_upgrade_section11_rerun_partials.sh` — rows 1 after-P0, 3, 5, 8 (fallback + modelPreset), 9, 10 if OANDA set, then pull + after_pull.
- **P0 after live:** `bash scripts/vps_section11_row1_after_p0.sh` — يفحص quota ثم يعيد صف 1 (`01-no-tools-after-p0.jsonl`) ويطبع `delta_in`؛ خط الأساس `01-no-tools.jsonl` أو أفضل `01-*` (يستثني after-p0). أو يدوياً: `bash scripts/mokli_upgrade_p0_live_delta.sh …`. على الدور الخفيف: **`provider_tools=3`** (chat فقط) أو **≤7** إذا وُجدت أدوات الجلسة (`read_session`…) في التسجيل — Agent API على VPS يظهر **7**؛ ما زال ≪ 11+ trading/filesystem.
- **جاهزية VPS:** `bash scripts/vps_section11_env_check.sh` — rev + API + OANDA + quota؛ `--require-quota` / `--require-oanda` قبل صفوف 11–10. **`blockers` / `operator_unblock`** يطبعان **`BLOCKERS_EXIT=`** / **`OPERATOR_UNBLOCK_EXIT=`** — لا تستخدم `| tail` عند فحص `$?` (استخدم `$?` مباشرة بعد الأمر). بعد `vps_pull_main.sh` أعد `quota_probe` مرة إذا ظهر JSONDecodeError (إعادة تشغيل Gateway).
- للاختبار على OpenRouter: اجعل `modelPreset` = `null` — وإلا يبقى `claude-opus-5` عبر `FallbackProvider`.
- بعد شحن Anthropic: أعد `modelPreset` = `claude-opus-5`. تشغيل صف: `MOKLI_SSH_HOST=… bash scripts/vps_section11_agent_api_turn.sh …`
- **OANDA:** غير مهيأ على `/opt/nanoagent` — `get_gold_quote` → `market_feed_unconfigured`. إما `docs/section11-vps-env.example` يدوياً، أو من workstation (لا يطبع الأسرار): `OANDA_API_TOKEN=… OANDA_ACCOUNT_ID=… bash scripts/vps_section11_set_oanda_env.sh` ثم `bash scripts/vps_section11_env_check.sh --require-oanda`.
- **صف 2 (2026-10-01):** prompt إنجليزي صريح للأداة → `tools=1` `rounds=2` `in≈25037` `out≈670`؛ أحداث `tool` started/failed + عرض «يفحص سعر الذهب…».
- **صف 4 (2026-10-01):** `Analyze gold…` → `run_trading_kernel` + بطاقة `structured`/`decision` **`res_…`** (verdict wait، OANDA not configured)؛ `tools=2` `rounds=3` `in≈24924`.

## قبل المحادثة الحية

0. `bash scripts/mokli_upgrade_section11_init.sh` — ينشئ `section11-events/` و`section11-results.json` (من القالب إن لم يوجد) ويطبع **§11 progress** (متوقع أن يفشل validate حتى اكتمال المسارات الحية؛ الخروج 0).
1. نشر فرع §11 على VPS: `bash scripts/vps_pull_main.sh cursor/section11-vps-rows-d9e1` (PR **#62** — **لا** `main` قبل merge) وتهيئة `~/.mokli/config.json` (مزود LLM، OANDA، MetaAPI حسب الإعداد).
2. `bash scripts/mokli_upgrade_operator_smoke.sh` — preflight + dry-run §11 للصف 1 + **init smoke** (مجلد مؤقت) + `pytest tests/scripts/`؛ **لا يستدعي LLM** و**لا يملأ §11 للإنتاج**. بديل أدق للصف 1 فقط: `bash scripts/mokli_upgrade_section11_dry_run.sh`. preflight منفصل: `bash scripts/mokli_upgrade_preflight.sh`.
3. في أنبوب Mokli: `SHOW_DIAGNOSTICS=true`.
4. Mokli UI + Gateway + Agent API (محلياً: Vite `5173` → API `8766`).
5. فحص جاهزية API: `curl http://127.0.0.1:5173/api/v2/health` أو `curl http://127.0.0.1:8766/api/v2/health`. منفذ `--port` على أمر `mokli gateway` (مثلاً `18791`) ليس مسار Agent API v2؛ طلب `/api/v2/health` عليه يعيد 404.

## مسار Agent API (تسجيل JSONL بدون أنبوب UI)

رمز Bearer (`nbat_…`) من إقران جهاز/عميل Gateway — **ليس** `nbat_test-bootstrap-token` من `tests/agent_api/conftest.py` (TestClient داخل pytest فقط؛ البوابة/Agent API الجاري يرفضه). قاعدة API: `http://127.0.0.1:8766/api/v2`.

```bash
BASE="http://127.0.0.1:8766/api/v2"
TOKEN="nbat_REPLACE_ME"
SID="$(curl -sf -X POST "$BASE/sessions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"section11-01"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")"

mkdir -p section11-events
curl -sfN "$BASE/sessions/$SID/events?until_end=1" \
  -H "Authorization: Bearer $TOKEN" \
  -o "section11-events/raw-01.sse" &
curl -sf -X POST "$BASE/sessions/$SID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"مرحبا، ما اسمك؟"}'
wait
grep '^data: ' section11-events/raw-01.sse | sed 's/^data: //' > section11-events/01-no-tools.jsonl
python scripts/mokli_upgrade_diagnostic_extract.py --file section11-events/01-no-tools.jsonl
```

كل سطر في `01-no-tools.jsonl` هو `GatewayEvent` (حقل `kind` و`data`). حدث `diagnostic` في `data` يطابق `TurnDiagnostics.to_dict()` — انظر `tests/fixtures/section11_turn_diagnostics_sample.jsonl`. Mokli UI + `mokli_pipe` يبقى مسار §11 للصفوف 12–13 (واجهة).

## تسمية ملفات JSONL (للـ batch)

| # | اسم ملف مقترح | مسار §11 |
| --- | --- | --- |
| 1 | `01-no-tools.jsonl` | تحية — `vps_section11_row1_greeting.sh`؛ بعد P0: `vps_section11_row1_after_p0.sh` |
| 2 | `02-single-tool.jsonl` | سعر الذهب — `bash scripts/vps_section11_row2_single_tool.sh` |
| 3 | `03-multi-tool.jsonl` | عدة أدوات — `bash scripts/vps_section11_row3_multi_tool.sh` (quota + get_gold_quote + list_dir) |
| 4 | `04-gold-analysis.jsonl` | تحليل / شراء — `bash scripts/vps_section11_row4_gold_analysis.sh` |
| 5 | `05-subagents.jsonl` | spawn / سرب — `bash scripts/vps_section11_row5_subagents.sh` |
| 6 | `06-tool-failure.jsonl` | فشل أداة — `bash scripts/vps_section11_row6_tool_failure.sh` |
| 7 | `07-retry.jsonl` | إعادة محاولة — `bash scripts/vps_section11_row7_retry.sh` |
| 8 | `08-fallback-provider.jsonl` | مزود بديل — `bash scripts/vps_section11_row8_fallback_provider.sh` (+ `modelPreset` على VPS) |
| 9 | `09-long-session-v3.jsonl` | جلسة طويلة — `bash scripts/vps_section11_row9_long_session.sh` (quota + 15× `list_dir`؛ `--session-summary` للطي) |
| 10 | `10-backtest.jsonl` | backtest — `bash scripts/vps_section11_row10_backtest.sh` (quota + OANDA) |
| 11 | `11-paper.jsonl` | ورقي — `bash scripts/vps_section11_row11_paper.sh` (يفحص quota ثم Agent API) |
| 12 | `12-desktop-ui.jsonl` | Mokli UI + Pipe — `bash scripts/vps_section11_row12_desktop.sh` ثم محادثة Pipe مع `SHOW_DIAGNOSTICS` |
| 13 | `13-mobile.jsonl` | هاتف/SDK — `bash scripts/vps_section11_row13_mobile.sh` (SDK smoke + تعليمات الجهاز) |

**صفوف 11–13 (تسلسل):** `bash scripts/mokli_upgrade_section11_remaining_rows.sh`
| 14 | `14-mt5-live.jsonl` | MT5 حي (اختياري) |

## بعد كل سينario من §11

1. احفظ تيار الأحداث JSONL (سطر JSON لكل حدث gateway/pipe). شكل التشخيص المتوقع: `{"kind":"diagnostic","data":{…}}` كما في `TurnDiagnostics.to_dict()` — مثال في `tests/fixtures/section11_turn_diagnostics_sample.jsonl`.
2. `python scripts/mokli_upgrade_diagnostic_extract.py --file events.jsonl` → سطر «الأرقام».
3. بعد عدة سينarios: احفظ `01-….jsonl` … `13-….jsonl` في مجلد واحد. انسخ `docs/section11-results.example.json` إلى `section11-results.json` واملأ «النتيجة» لكل صف.  
   `python scripts/mokli_upgrade_section11_batch.py --dir ./section11-events/ --results section11-results.json --markdown`  
   → صفوف جاهزة للصق في §11 (النتيجة + الأرقام).
4. لقطة شاشة لسطر/تفاصيل النشاط إن أمكن.

## قبل تحديث §11 في التقرير

```bash
python scripts/mokli_upgrade_section11_validate.py \
  --dir ./section11-events --results section11-results.json --require-through 13
python scripts/mokli_upgrade_section11_patch_report.py \
  --dir ./section11-events --results section11-results.json \
  --report docs/mokli-agent-upgrade-report.md --dry-run
# أو: bash scripts/mokli_upgrade_section11_close.sh (validate+batch+dry-run) ثم --apply
```

## بعد `section11_close.sh --apply`

عند `--require-through 13` على `docs/mokli-agent-upgrade-report.md`، يشغّل `close` **بوابة التقرير** تلقائياً (`test_mokli_upgrade_report_section11_gate.py`). للتحقق اليدوي أو مسار تقرير آخر:

```bash
pytest tests/scripts/test_mokli_upgrade_report_section11_gate.py -q
git diff docs/mokli-agent-upgrade-report.md   # commit التقرير + artifacts refs مع الفرع
```

يجب أن يمرّ gate (عنوان VPS + صفوف 1–13 مملوءة بلا `DRY-RUN`؛ الصف 14 اختياري).

يجب أن يطبع `OK §11 artifacts` — يثبت وجود JSONL + diagnostic + «النتيجة» غير فارغة لكل صف مطلوب (لا يثبت صحة السلوك الحي). عند الفشل يطبع `validate` جدول **§11 progress** (ready / incomplete لكل صف). نصوص `DRY-RUN` من التجربة الجافة **تُرفض** عند `--require-through` ≥ 2. `docs/section11-results.example.json` **لا يمرّ** `--require-through 13` (قالب فقط). `patch_report` يشغّل validate تلقائياً ما لم تُمرّر `--skip-validate`. عند `--apply` وصفوف 1–`require-through` مكتملة، يُحدَّث عنوان §11 من «لم تُنفَّذ في Cloud Agent» إلى «تم التعبئة من تشغيل VPS» (المطابقة تتسامح مع اختلاف تركيب علامات «نُفِّذ» في Markdown).

## Cloud Agent — مؤقت بعد reset OpenRouter

على جلسة Cloud Agent نشطة، يمكن جدولة متابعة تلقائية باسم **`mokli-section11-after-openrouter-reset`** (one-shot بعد `X-RateLimit-Reset` + buffer). عند الإطلاق: `vps_pull_main.sh` → `quota_probe` → **`timer_wake --wait-quota`** → إغلاق §11 عند اكتمال JSONL. **لا يغني** عن OANDA وصفوف 11–13 (UI/جهاز). للتحقق: `list_subscriptions` (MCP) أو أعد الجدولة يدوياً: `bash scripts/mokli_upgrade_section11_timer_wake.sh --wait-quota`.

## PR §11 (قبل الدمج في main)

- فرع: `cursor/section11-vps-rows-d9e1` — [PR #62](https://github.com/loorksy/NanoAgent/pull/62)
- على VPS حتى الدمج: `MOKLI_BRANCH=cursor/section11-vps-rows-d9e1 bash scripts/vps_pull_main.sh`
- بعد الدمج: `MOKLI_BRANCH=main bash scripts/vps_pull_main.sh`

## ما نرسله لجلسة لاحقة

- ملف JSONL أو `--json` كامل من السكربت.
- لقطة §11 مع عمودي «النتيجة» و«الأرقام» مملوءين.
- أي `diagnostic` يظهر في واجهة المطور.

## ما لا يُعتبر إغلاقاً

- pytest وحده.
- health على `8766` أو عبر Vite `5173` بدون محادثة مزود (مفاتيح LLM فارغة في Cloud Agent).
- اختبار §11.1 (ارتباط CI) بدل الصفوف 1–13 الحية.
- `section11_dry_run` أو `operator_smoke` أو `section11_close` على fixture/صف 1 فقط.
- `patch_report --apply` قبل `validate --require-through 13` على artifacts حية كاملة.
- `close --apply` على التقرير الرسمي مع artifacts ناقصة (يفشل validate ولا يعدّل `docs/mokli-agent-upgrade-report.md` — `test_close_apply_on_canonical_report_aborts_before_patch`).
