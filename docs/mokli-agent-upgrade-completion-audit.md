# تدقيق إغلاق ترقية Mokli (بوابة الإنتاج)

هذا الملف **لا يغني** عن §11 في `docs/mokli-agent-upgrade-report.md`. يوضح ما ثبت بالكود والاختبارات، وما يبقى للمشغّل على VPS.

| المتطلب | دليل الإنجاز | الحالة |
| --- | --- | --- |
| فرع مستقل + commits صغيرة | دُمج في **`main`** (`9b1a3f58` وما بعد) | منجز |
| Phase 0 — تدقيق من الكود | `docs/mokli-agent-upgrade-audit.md` | منجز |
| P0 — تقليل توكن/تأخير/حلقات أدوات بلا `max_tokens` قسري ولا حذف عشوائي للسجل | §2 + عقود مضغوطة + تأجيل مخططات التداول على الدور الخفيف؛ `test_turn_efficiency`؛ تقدير `final≈4652` للتحية (محلي) | منجز (وحدة/تقدير) |
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
| pytest مجمّع | `tests/agent` + `tests/trading` + `tests/agent_api` + `test_mokli_pipe.py` + `tests/scripts/` → **2375** ناجية (1 skipped) | منجز |
| أدوات المشغّل §11 | … + `blockers` (`--require-through`، `--skip-vps` للصفوف 1–10)، `production_gate` → blockers | منجز |
| §11 بوابة تقرير (CI) | `tests/scripts/test_mokli_upgrade_report_section11_gate.py`؛ `test_section11_close_apply_updates_real_report_unicode_header`؛ `test_close_apply_on_canonical_report_aborts_before_patch` | منجز |
| **إغلاق الترقية للإنتاج** | §11: عمودا «النتيجة» و«الأرقام» لصفوف 1–13 (+14 اختياري) | **غير منجز** (تقرير: **جزئي** 1–2) |
| VPS checkout (Hostinger) | **`3b4d30a2`** on `cursor/section11-vps-rows-d9e1` (PR #62)؛ quota **BLOCKED**؛ OANDA off؛ batch row 9 `session-summary`؛ rerun partials v2/v3 names | **منجز** |
| GitHub Actions (PR #62) | Jobs fail in ~5s with **empty steps** / log 404 (all matrix jobs)؛ local aggregate pytest **2375** green | **infra** — re-run workflow on GitHub |
| §11 حي على VPS | **1–2** PASS؛ **3** PARTIAL؛ **4–6** PASS؛ **5** PARTIAL؛ **7** PASS؛ **8** PASS (retry `cleared`)؛ **9** PARTIAL (15 rounds؛ OpenRouter quota)؛ **10** PARTIAL (backtest؛ OANDA off)؛ **11–13** فارغة | **جزئي** |

## أوامر تحقق سريعة (محلي)

```bash
bash scripts/mokli_upgrade_operator_smoke.sh   # preflight + §11 dry-run + init smoke + tests/scripts (no LLM)
bash scripts/mokli_upgrade_section11_cloud_status.sh   # quota probe + blockers --skip-vps (Cloud Agent)
bash scripts/mokli_upgrade_section11_init.sh # VPS: events/ + results + progress (no LLM)
pytest tests/agent tests/trading tests/agent_api tests/deploy/test_mokli_pipe.py tests/scripts/ -q
```

## Cloud Agent (هذا الـ VM)

بدون مفاتيح LLM/OANDA/MetaAPI في `~/.mokli/config.json` أو البيئة، **لا يمكن** تنفيذ صفوف §11 1–13 هنا. SSH بمفتاح (`MOKLI_SSH_HOST`) يكفي لـ `sync_from_vps` و`quota_probe` و`blockers --skip-vps`، لكن **`row1_after_p0` يتوقف عند quota** (`probe_exit=1`، 2026-10-01). المزيد من pytest **لا يغلق** الهدف.

## بعد VPS (المشغّل)

اتبع **قائمة الإغلاق (9 خطوات)** في `docs/mokli-agent-upgrade-operator-handoff.md`: credits + OANDA → `rerun_partials` → 11–13 → `sync_from_vps` (`p0-interim-summary.txt`) → `blockers` exit 0 → `section11_close.sh --apply --require-through 13` → gate pytest.
