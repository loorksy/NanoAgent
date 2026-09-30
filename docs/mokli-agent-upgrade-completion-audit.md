# تدقيق إغلاق ترقية Mokli (بوابة الإنتاج)

هذا الملف **لا يغني** عن §11 في `docs/mokli-agent-upgrade-report.md`. يوضح ما ثبت بالكود والاختبارات، وما يبقى للمشغّل على VPS.

| المتطلب | دليل الإنجاز | الحالة |
| --- | --- | --- |
| فرع مستقل + commits صغيرة | `cursor/agent-runtime-efficiency-d9e1` | منجز |
| Phase 0 — تدقيق من الكود | `docs/mokli-agent-upgrade-audit.md` | منجز |
| P0 — تقليل توكن/تأخير/حلقات أدوات بلا `max_tokens` قسري ولا حذف عشوائي للسجل | `docs/mokli-agent-upgrade-report.md` §1–2؛ `tests/agent/test_turn_efficiency.py` | منجز (قياس محلي/وحدة) |
| P0 — أرقام before/after على **مزود حي** | جدول §11 عمود «الأرقام» | **معلق** |
| Agent API ينشر `diagnostic` في SSE | `tests/agent_api/test_sessions_routes.py::test_sse_diagnostic_matches_section11_extract` | منجز (CI، ليس §11 حي) |
| P1 — نشاط UI من أحداث وقت التشغيل فقط | `tests/deploy/test_mokli_pipe.py`؛ `mokli-ui` / `mobile` | منجز (CI)؛ **§11 صفوف 12–13 حية** |
| P1 — طبقات سياق حسب المهمة | `mokli/agent/context_layers.py`؛ اختبارات الطبقات | منجز |
| P1 — وكلاء تداول + نقاش/فرعي موجود | `mokli/trading/crew/`؛ `tests/trading/test_i18n_catalog.py` | منجز |
| P1 — قرارات تداول منظمة | `result_wire`؛ `mokli_pipe`؛ بطاقة `decision` | منجز (CI)؛ **§11 صف 4 حي** |
| P2 — منشئ استراتيجية على النواة الحالية | `strategy_spec`، `propose_strategy`، `fast_backtest`؛ تقرير §6 | منجز (وحدة)؛ **§11 صف 10–11 حي** |
| P2 — تدقيق إعدادات | `docs/mokli-settings-audit.md` | منجز |
| P3 — تصنيف إرث Open WebUI؛ حذف المثبت غير الموصول فقط | تقرير §8؛ حذف `stage_checkpoint` / `trace_events` | منجز |
| تقرير نهائي (مشاكل، توكن، سرعة، أدوات، وكلاء، استراتيجية، إعدادات، إرث، اختبارات، ملفات) | `docs/mokli-agent-upgrade-report.md` §1–10 | منجز |
| لا أنظمة AgentRunner/ToolRegistry/Memory/TradingKernel موازية | مراجعة الفرع — توسيع الموجود | منجز |
| pytest مجمّع | `tests/agent` + `tests/trading` + `tests/agent_api` + `test_mokli_pipe.py` + `tests/scripts/` → **2319** ناجية (1 skipped) | منجز |
| أدوات المشغّل §11 | `operator_smoke.sh`، `section11_close.sh` (validate+batch+patch)، `preflight`، `dry_run`، `extract`، `batch`، `validate`، `patch_report` (+ `section11-results.example.json`، fixture JSONL) | منجز |
| **إغلاق الترقية للإنتاج** | §11: عمودا «النتيجة» و«الأرقام» لصفوف 1–13 (+14 اختياري) | **غير منجز** |

## أوامر تحقق سريعة (محلي)

```bash
bash scripts/mokli_upgrade_operator_smoke.sh   # preflight + §11 dry-run + tests/scripts (no LLM)
pytest tests/agent tests/trading tests/agent_api tests/deploy/test_mokli_pipe.py tests/scripts/ -q
```

## Cloud Agent (هذا الـ VM)

بدون مفاتيح LLM/OANDA/MetaAPI في `~/.mokli/config.json` أو البيئة، **لا يمكن** تنفيذ صفوف §11 1–13 هنا. المزيد من سكربتات المشغّل أو pytest **لا يغلق** الهدف؛ الخطوة التالية على VPS فقط.

## بعد VPS

اتبع `docs/mokli-agent-upgrade-operator-handoff.md`، املأ `section11-results.json`، ثم `bash scripts/mokli_upgrade_section11_close.sh` و`--apply` لتحديث §11 في التقرير (أو PR).
