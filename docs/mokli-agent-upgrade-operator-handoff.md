# تسليم ترقية Mokli — للمشغّل (بعد Cloud Agent)

## الفرع

- `cursor/agent-runtime-efficiency-d9e1` (أساس الدمج: `cursor/broker-market-feed-d9e1`)
- راجع `git log -1` على الفرع بعد آخر دفع

## ما اكتمل بدون VPS

- `docs/mokli-agent-upgrade-audit.md` — تدقيق المرحلة 0
- `docs/mokli-agent-upgrade-report.md` — §1–11.1 (جدول §11 **فارغ** حتى التشغيل الحي)
- `docs/mokli-settings-audit.md` — P2/P3 إعدادات
- `docs/mokli-agent-upgrade-completion-audit.md` — بوابة إغلاق (ما ثبت vs §11 المعلق)
- pytest: **2313** ناجية (مجمّع + سكربتات §11 في `tests/scripts/`)

## قبل المحادثة الحية

1. نشر الفرع وتهيئة `~/.mokli/config.json` (مزود LLM، OANDA، MetaAPI حسب الإعداد).
2. `bash scripts/mokli_upgrade_operator_smoke.sh` — preflight (صحة API + تحذير المفاتيح) + dry-run §11 للصف 1 + `pytest tests/scripts/`؛ **لا يستدعي LLM** و**لا يملأ §11 للإنتاج**. بديل أدق للصف 1 فقط: `bash scripts/mokli_upgrade_section11_dry_run.sh`. preflight منفصل: `bash scripts/mokli_upgrade_preflight.sh`.
3. في أنبوب Mokli: `SHOW_DIAGNOSTICS=true`.
4. Mokli UI + Gateway + Agent API (محلياً: Vite `5173` → API `8766`).
5. فحص جاهزية API: `curl http://127.0.0.1:5173/api/v2/health` أو `curl http://127.0.0.1:8766/api/v2/health`. منفذ `--port` على أمر `mokli gateway` (مثلاً `18791`) ليس مسار Agent API v2؛ طلب `/api/v2/health` عليه يعيد 404.

## مسار Agent API (تسجيل JSONL بدون أنبوب UI)

رمز Bearer (`nbat_…`) من إقران جهاز/عميل Gateway. قاعدة API: `http://127.0.0.1:8766/api/v2`.

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
```

يجب أن يطبع `OK §11 artifacts` — يثبت وجود JSONL + diagnostic + «النتيجة» غير فارغة لكل صف مطلوب (لا يثبت صحة السلوك الحي). نصوص `DRY-RUN` من التجربة الجافة **تُرفض** عند `--require-through` ≥ 2.

## ما نرسله لجلسة لاحقة

- ملف JSONL أو `--json` كامل من السكربت.
- لقطة §11 مع عمودي «النتيجة» و«الأرقام» مملوءين.
- أي `diagnostic` يظهر في واجهة المطور.

## ما لا يُعتبر إغلاقاً

- pytest وحده.
- health على `8766` أو عبر Vite `5173` بدون محادثة مزود (مفاتيح LLM فارغة في Cloud Agent).
- اختبار §11.1 (ارتباط CI) بدل الصفوف 1–13 الحية.
