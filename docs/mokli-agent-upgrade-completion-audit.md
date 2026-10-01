# تدقيق إغلاق ترقية Mokli (بوابة الإنتاج)

هذا الملف **لا يغني** عن §11 في `docs/mokli-agent-upgrade-report.md`. يوضح ما ثبت بالكود والاختبارات، وما يبقى للمشغّل على VPS.

| المتطلب | دليل الإنجاز | الحالة |
| --- | --- | --- |
| فرع مستقل + commits صغيرة | PR **#62** — `cursor/section11-vps-rows-d9e1` (يتقدّم على **`main`**؛ merge بعد إغلاق §11) | منجز (فرع)؛ **merge** بعد §11 |
| Phase 0 — تدقيق من الكود | `docs/mokli-agent-upgrade-audit.md` | منجز |
| P0 — تقليل توكن/تأخير/حلقات أدوات بلا `max_tokens` قسري ولا حذف عشوائي للسجل | §2 + عقود مضغوطة + تأجيل مخططات التداول على الدور الخفيف؛ `test_turn_efficiency`؛ تقدير `final≈5159` للتحية (محلي، `p0_turn_estimate --compare`) | منجز (وحدة/تقدير) |
| P0 — أرقام before/after على **مزود حي** | تقرير §2.1 + §11؛ إعادة قياس after credits/OANDA | **جزئي** (baseline VPS) |
| Agent API ينشر `diagnostic` في SSE | `tests/agent_api/test_sessions_routes.py::test_sse_diagnostic_matches_section11_extract` | منجز (CI، ليس §11 حي) |
| P1 — نشاط UI من أحداث وقت التشغيل فقط | `tests/deploy/test_mokli_pipe.py`؛ `mokli-sdk`؛ `mokli_upgrade_section11_row13_ci.sh` (Cloud Agent 2026-10-01) | منجز (CI/proxy)؛ **§11 صفوف 12–13 JSONL حية** |
| P1 — طبقات سياق حسب المهمة | `mokli/agent/context_layers.py`؛ اختبارات الطبقات | منجز |
| P1 — وكلاء تداول + نقاش/فرعي موجود | `mokli/trading/crew/`؛ `tests/trading/test_i18n_catalog.py` | منجز |
| P1 — قرارات تداول منظمة | `result_wire`؛ `mokli_pipe`؛ بطاقة `decision` | منجز (CI)؛ **§11 صف 4 حي** |
| P2 — منشئ استراتيجية على النواة الحالية | `strategy_spec`، `propose_strategy`، `fast_backtest`؛ تقرير §6 | منجز (وحدة)؛ **§11 صف 10–11 حي** |
| P2 — تدقيق إعدادات | `docs/mokli-settings-audit.md` | منجز |
| P3 — تصنيف إرث Open WebUI؛ حذف المثبت غير الموصول فقط | تقرير §8؛ حذف `stage_checkpoint` / `trace_events` | منجز |
| تقرير نهائي (مشاكل، توكن، سرعة، أدوات، وكلاء، استراتيجية، إعدادات، إرث، اختبارات، ملفات) | `docs/mokli-agent-upgrade-report.md` §1–10 | منجز |
| لا أنظمة AgentRunner/ToolRegistry/Memory/TradingKernel موازية | مراجعة الفرع — توسيع الموجود | منجز |
| pytest مجمّع | `tests/agent` + `tests/trading` + `tests/agent_api` + `test_mokli_pipe.py` + `tests/scripts/` → **2462** ناجية (1 skipped؛ `bash scripts/mokli_upgrade_aggregate_pytest.sh`) | منجز |
| أدوات المشغّل §11 | `validate.sh`؛ `blockers` (`blockers_summary`)؛ `close.sh` (`close_summary`)؛ `production_gate`؛ sync @13؛ `p0_live_delta`؛ `quota_probe` + `section11_probe_cache_preserve.py`؛ `completion_status` / `cloud_status` / `operator_unblock` / `section11_status` (`seconds_until_reset` + `partial10_*`)؛ `try_row11_paper.sh` في `after_reset_wake`/`timer_wake`؛ `remaining_rows.sh` (دليل 12–13)؛ `timer_wake`؛ `check_wake.sh` (tmux+log)؛ `operator_smoke` | منجز |
| §11 بوابة تقرير (CI) | `validate` @13: after-p0 **`in>0`**؛ صفوف **3–13** (جودة + 11 paper + 12 structured + 13 activity)؛ `pick_row` **`v2`/`in>0`**؛ `close --apply` → §2.1 | منجز |
| **إغلاق الترقية للإنتاج** | §11: عمود «النتيجة» و«الأرقام» لصفوف 1–13 (+14 اختياري) | **غير منجز** (VPS جزئي 1–10؛ **`close.sh @13` يرفض** عبر validate؛ **11–13** فارغة؛ **after-P0**؛ PARTIAL **3,5,9,10**) |
| VPS checkout (Hostinger) | PR #62؛ **`git_rev=157d60ef`** (VPS: `oanda_configured=no`, `llm_quota=BLOCKED`؛ reset ≈ **2026-10-02 00:00 UTC**)؛ `blockers` يطبع **`closure_errors=N`** (9 على الحزمة الجزئية @13)؛ preset **`qwen3-8-27b-free`** | منجز (rev)؛ **quota/OANDA** محجوز |
| GitHub Actions (PR #62) | Jobs fail in ~2s: **account locked (billing)** — no runner logs؛ local aggregate pytest **2462** green (2026-10-01) | **infra** — fix GitHub billing then re-run workflow |
| §11 حي على VPS | **1–2** PASS؛ **3** PARTIAL؛ **4–6** PASS؛ **5** PARTIAL؛ **7** PASS؛ **8** PASS (retry `cleared`؛ **`in=0` في JSONL** — أعد `row8_fallback` بعد quota)؛ **9** PARTIAL؛ **10** PARTIAL (OANDA off)؛ **11–13** فارغة؛ **صف 12** pre-check (VPS + Cloud `local_section11_row12_smoke`): `ui_http=200` + `pipe_show_diagnostics` (2026-10-01) | **جزئي** |

## أوامر تحقق سريعة (محلي)

```bash
bash scripts/mokli_upgrade_operator_smoke.sh   # preflight + §11 dry-run + init smoke + tests/scripts (no LLM)
bash scripts/mokli_upgrade_section11_cloud_status.sh   # cached quota + blockers --skip-vps (Cloud Agent)
bash scripts/mokli_upgrade_section11_completion_status.sh   # branch + reset + cached quota + artifacts @13 (+ partial10 gate when blocked)
bash scripts/mokli_upgrade_section11_timer_wake.sh --wait-quota   # after reset: Cloud Agent timer chain
bash scripts/mokli_upgrade_section11_operator_unblock.sh   # live probe + env + blockers @13 (operator)
bash scripts/vps_section11_quota_status.sh   # last quota-probe JSONL (no LLM)
bash scripts/mokli_upgrade_section11_init.sh # VPS: events/ + results + progress (no LLM)
bash scripts/mokli_upgrade_aggregate_pytest.sh
```

## Cloud Agent (هذا الـ VM)

بدون مفاتيح LLM/OANDA/MetaAPI في `~/.mokli/config.json` أو البيئة، **لا يمكن** تنفيذ صفوف §11 1–13 هنا. **Cloud Agent (tmux):** قد يُشغَّل `bash scripts/mokli_upgrade_section11_timer_wake.sh --wait-quota` في جلسة `section11-timer-wake-wait` (سجل: `/opt/cursor/artifacts/timer_wake_wait_quota.log`) لتنفيذ إعادة الصفوف على VPS بعد reset تلقائياً — OANDA/صفوف 11–13 ما زالت تحتاج المشغّل. بعد إعادة تعيين OpenRouter: **`bash scripts/mokli_upgrade_section11_timer_wake.sh --wait-quota`** (انتظار reset إن لزم → `after_reset_wake` → … → `close --apply @13`). بدون انتظار: `after_reset_wake.sh` أو `post_quota.sh --wait --pull-vps`. SSH بمفتاح (`MOKLI_SSH_HOST`) يكفي لـ `sync_from_vps` و`quota_probe` و`blockers --skip-vps`؛ **`cloud_status --require-through 10`** يخرج **0** عندما حزمة JSONL 1–10 محلية سليمة (حتى مع quota محجوب). **`vps_section11_quota_status.sh`** / **`quota_probe`** يطبعان **≈وقت إعادة تعيين OpenRouter** من `X-RateLimit-Reset` في `quota-probe.jsonl` (مثلاً **2026-10-02 00:00 UTC** عند حد free-models-per-day). **`row1_after_p0` / إغلاق 13** يتوقفان حتى quota OK (`in>0`) أو credits/`MOKLI_SECTION11_MODEL`. المزيد من pytest **لا يغلق** الهدف. **مؤقت Cursor (one-shot):** `mokli-section11-after-openrouter-reset` — يُعاد جدولته بعد `wait_quota_reset`؛ المتابعة تشغّل **`timer_wake --wait-quota`** (OANDA ما زال يحتاج المشغّل).

## بعد VPS (المشغّل)

اتبع **قائمة الإغلاق (9 خطوات)** في `docs/mokli-agent-upgrade-operator-handoff.md`: credits + OANDA → **`timer_wake --wait-quota`** (أو خطوة بخطوة) → `blockers` exit 0 → `section11_close.sh --apply --require-through 13 --results section11-results-partial.json` → gate pytest.
