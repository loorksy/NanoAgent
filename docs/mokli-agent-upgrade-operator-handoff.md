# تسليم ترقية Mokli — للمشغّل (بعد Cloud Agent)

## الفرع

- `cursor/agent-runtime-efficiency-d9e1` (أساس الدمج: `cursor/broker-market-feed-d9e1`)
- راجع `git log -1` على الفرع بعد آخر دفع

## ما اكتمل بدون VPS

- `docs/mokli-agent-upgrade-audit.md` — تدقيق المرحلة 0
- `docs/mokli-agent-upgrade-report.md` — §1–11.1 (جدول §11 **فارغ** حتى التشغيل الحي)
- `docs/mokli-settings-audit.md` — P2/P3 إعدادات
- pytest: **2296** ناجية (مجمّع + `tests/scripts/test_mokli_upgrade_diagnostic_extract.py`)

## قبل المحادثة الحية

1. نشر الفرع وتهيئة `~/.mokli/config.json` (مزود LLM، OANDA، MetaAPI حسب الإعداد).
2. في أنبوب Mokli: `SHOW_DIAGNOSTICS=true`.
3. Mokli UI + Gateway + Agent API (محلياً: Vite `5173` → API `8766`).

## بعد كل سينario من §11

1. احفظ تيار الأحداث JSONL (سطر JSON لكل حدث gateway/pipe).
2. `python scripts/mokli_upgrade_diagnostic_extract.py --file events.jsonl` → سطر «الأرقام».
3. لقطة شاشة لسطر/تفاصيل النشاط إن أمكن.

## ما نرسله لجلسة لاحقة

- ملف JSONL أو `--json` كامل من السكربت.
- لقطة §11 مع عمودي «النتيجة» و«الأرقام» مملوءين.
- أي `diagnostic` يظهر في واجهة المطور.

## ما لا يُعتبر إغلاقاً

- pytest وحده.
- health `curl /api/v2/health` بدون محادثة مزود.
- اختبار §11.1 (ارتباط CI) بدل الصفوف 1–13 الحية.
