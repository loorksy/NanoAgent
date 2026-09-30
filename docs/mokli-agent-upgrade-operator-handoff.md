# تسليم ترقية Mokli — للمشغّل (بعد Cloud Agent)

## الفرع

- `cursor/agent-runtime-efficiency-d9e1` (أساس الدمج: `cursor/broker-market-feed-d9e1`)
- راجع `git log -1` على الفرع بعد آخر دفع

## ما اكتمل بدون VPS

- `docs/mokli-agent-upgrade-audit.md` — تدقيق المرحلة 0
- `docs/mokli-agent-upgrade-report.md` — §1–11.1 (جدول §11 **فارغ** حتى التشغيل الحي)
- `docs/mokli-settings-audit.md` — P2/P3 إعدادات
- pytest: **2299** ناجية (مجمّع + سكربتات §11 في `tests/scripts/`)

## قبل المحادثة الحية

1. نشر الفرع وتهيئة `~/.mokli/config.json` (مزود LLM، OANDA، MetaAPI حسب الإعداد).
2. `bash scripts/mokli_upgrade_preflight.sh` — صحة Agent API، تحذير إن مفاتيح المزود فارغة، تذكير بسكربت الأرقام (لا يستدعي LLM).
3. في أنبوب Mokli: `SHOW_DIAGNOSTICS=true`.
4. Mokli UI + Gateway + Agent API (محلياً: Vite `5173` → API `8766`).
5. فحص جاهزية API: `curl http://127.0.0.1:5173/api/v2/health` أو `curl http://127.0.0.1:8766/api/v2/health`. منفذ `--port` على أمر `mokli gateway` (مثلاً `18791`) ليس مسار Agent API v2؛ طلب `/api/v2/health` عليه يعيد 404.

## تسمية ملفات JSONL (للـ batch)

| # | اسم ملف مقترح | مسار §11 |
| --- | --- | --- |
| 1 | `01-no-tools.jsonl` | تحية / بلا أدوات |
| 2 | `02-single-tool.jsonl` | سعر الذهب |
| 3 | `03-multi-tool.jsonl` | عدة أدوات |
| 4 | `04-gold-analysis.jsonl` | تحليل / شراء |
| 5 | `05-subagents.jsonl` | spawn / سرب |
| 6 | `06-tool-failure.jsonl` | فشل أداة |
| 7 | `07-retry.jsonl` | إعادة محاولة |
| 8 | `08-fallback-provider.jsonl` | مزود بديل |
| 9 | `09-long-session.jsonl` | جلسة طويلة |
| 10 | `10-backtest.jsonl` | backtest / مختبر |
| 11 | `11-paper.jsonl` | ورقي |
| 12 | `12-desktop-ui.jsonl` | Mokli UI (اختياري للأرقام؛ لقطة للنتيجة) |
| 13 | `13-mobile.jsonl` | هاتف/SDK |
| 14 | `14-mt5-live.jsonl` | MT5 حي (اختياري) |

## بعد كل سينario من §11

1. احفظ تيار الأحداث JSONL (سطر JSON لكل حدث gateway/pipe).
2. `python scripts/mokli_upgrade_diagnostic_extract.py --file events.jsonl` → سطر «الأرقام».
3. بعد عدة سينarios: احفظ `01-….jsonl` … `13-….jsonl` في مجلد واحد، ثم  
   `python scripts/mokli_upgrade_section11_batch.py --dir ./section11-events/ --markdown`  
   للصق عمود الأرقام في §11 (النتيجة ما زالت يدوية).
4. لقطة شاشة لسطر/تفاصيل النشاط إن أمكن.

## ما نرسله لجلسة لاحقة

- ملف JSONL أو `--json` كامل من السكربت.
- لقطة §11 مع عمودي «النتيجة» و«الأرقام» مملوءين.
- أي `diagnostic` يظهر في واجهة المطور.

## ما لا يُعتبر إغلاقاً

- pytest وحده.
- health على `8766` أو عبر Vite `5173` بدون محادثة مزود (مفاتيح LLM فارغة في Cloud Agent).
- اختبار §11.1 (ارتباط CI) بدل الصفوف 1–13 الحية.
