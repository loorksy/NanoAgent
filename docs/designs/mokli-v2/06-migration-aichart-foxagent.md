# 06 — ترحيل الميزات من AiChart و foxagent

> جزء من خطة Mokli v2 — انظر [`00-master-plan.md`](./00-master-plan.md)
> المصدر: مسح `loorksy/AiChart` (TypeScript/Next.js + `research-service` Python + `admin_android` Kotlin + `admin_flutter`) و`loorksy/foxagent` (FastAPI + Next.js) مقابل `mokli/` و`mokli/`.

---

## 1. ما هو موجود أصلاً في Mokli ولا يُعاد ترحيله

أنبوبة AiChart (`orchestrator` → specialists → synthesizer → gates)، TradingView widget + `chart-host`، نقاش foxagent (Bull/Bear/Risk)، منسّق البوتات (multi_strategy/pattern_notes/news_candle)، swarm presets، OANDA، MetaAPI propose/confirm، دفتر التداول الورقي، Telegram/WhatsApp/WebSocket، i18n عربي/إنجليزي، kill switch، bad tick، الأرقام السحرية، تبني الصفقات اليدوية، PWA.

## 2. مبدأ الترحيل

- **نرحّل السلوك لا الكود.** Python (foxagent) يُنقل بإعادة كتابة مطابقة لمعايير المستودع (`TypedDict` عند الحد، لا `Any`، اختبار لكل وحدة). TypeScript (AiChart) في الخلفية يُترجَم إلى Python؛ في الواجهة تُنقل **المكونات كأنماط** إلى الـ fork من Mokli (`loorksy/mokli-mokli`، مسارات Svelte مضافة) أو إلى قوالب النتائج المنظّمة في `mokli/agent_api/render/` (04, 07).
- كل ميزة مرحّلة تُربط بقدرة في 03 أو بقسم في 04/05؛ ما لا يربط بهما يُرفض (billing، ads، support inbox، multi-tenant admin).
- لا يُلمس `/opt/foxagent` في الإنتاج؛ المصدر هو git فقط.

## 3. قائمة الترحيل المعتمدة (مرتبة بالقيمة)

| # | الميزة | المصدر | الوجهة في Mokli | يُغلق | الحجم |
|---|---|---|---|---|---|
| R1 | **محرك backtest** + مقاييس (orders/positions/metrics/attribution) + walk-forward / Monte Carlo / bootstrap | `aichart/research-service/` (Python) + `foxagent/backend/app/services/backtest/` (TP1 partial, BE, spread cost) | `mokli/trading/backtest/{engine,metrics,validation}.py` + أداة `fast_backtest(strategy, candles=200)` | T-5.2 | L |
| R2 | **مخزن أسرار مشفّر (Fernet)** | `foxagent/.../settings_store.py` | `mokli/security/secret_store.py`؛ يُستخدم لـ MetaAPI/OANDA/Telegram tokens؛ المفتاح من keyring أو `MOKLI_SECRET_KEY` | T-7.2 | S |
| R3 | **مستودع شموع الذهب + مزامنة وصحة البيانات** | `foxagent/.../gold_warehouse.py`, `gold_sync.py` | `mokli/trading/warehouse.py` (SQLite OHLC M1→D1، فجوات، آخر مزامنة) — يغذّي R1 وT-1.2 | T-1.2, T-5.2 | M |
| R4 | **Approval Inbox** (إشارات مُرحَّلة/ترقية إشارة بوت إلى تحليل كامل/ack) | `foxagent/.../inbox.py` + `frontend/.../inbox` | يُدمج في قسم **Tasks** (الاقتراحات المنتظرة) وقسم **التوصيات** (04) | T-6.2 | M |
| R5 | **قاطع دائرة لكل استراتيجية + Safe Mode** | `foxagent/.../trading_bot/circuit.py` | `mokli/trading/bots/circuit.py` + عرض في Tasks | 3.4/3.2 توسعة | S |
| R6 | **ChatReasoning** خط زمني حي للوكلاء أثناء النقاش | `foxagent/frontend/.../ChatReasoning.tsx` | Timeline في الـ Pipe (`<details>` من أحداث `tool`/`subagent` — 07 §4) + مكوّن RN `Timeline` (05) | «وكلاء يتناقشون» مرئي | M |
| R7 | **Closed-market scenario** كامل (خطة عطلة نهاية الأسبوع للافتتاح) | AiChart orchestrator `resolveClosedMarketScenario` | `mokli/trading/closed_market.py` (موجود كبطاقة فقط) + نتيجة `scenario_notice` | 9.3 / 6.3 | S |
| R8 | **Case memory / similar-cases indexer** (بصمة + تشابه + نتيجة) | `aichart/src/lib/marketMemory/` | توسيع `intel/vector_playbook.py` + `intel/dtw_matcher.py` بفهرس حالات SQLite ونتائجها | 5.1 تعميق | M |
| R9 | **مزوّد COT مخصص** (CFTC Socrata) | `aichart/src/lib/agent/macro/cotProvider.ts` | `mokli/trading/intel/cot.py` (عبر `security/network.py`) | 2.x | S |
| R10 | **Learning loop** (نتيجة → درس كدليل لا كحجب) | `aichart/src/lib/agent/learningLoop.ts` | توسيع `intel/postmortem.py` بدروس مرجّحة تُحقن كـ evidence node `lessons` | 5.4 | S |
| R11 | **Scenario memory L2** (ملف نتائج السيناريوهات لكل نظام سوق) | `aichart/.../memory/scenarioMemory.ts` | `mokli/trading/memory/scenarios.py` | 5.1/5.3 | S |
| R12 | **Journal / post-mortem UI** | `foxagent/.../journal.py` + صفحة | قسم **السجل** (04) — تبويب Journal | 5.3 / 9.4 | S |
| R13 | **Economic calendar view** | `foxagent/.../economic_calendar.py` + صفحة | تبويب داخل **السجل** أو artifact `macro_dashboard` | 2.1 | S |
| R14 | **Strategy Lab** (اقتراح/تحقق/قائمة استراتيجيات + backtest) | `foxagent/.../strategy_library.py` + `strategy-lab` | مرحلة لاحقة — يعتمد على R1+R3؛ يظهر كأداة `propose_strategy` وتبويب في Tasks | 5.2 توسعة | L |
| R15 | **Bot desk** (instances, circuits, live signals) | `foxagent/frontend/.../bots` | يُدمج في **Tasks** كبطاقات «مهام مستمرة» — لا صفحة مستقلة | 8.1 | M |
| R16 | **Tradability calibration cron** + **event monitor** للخطط المفتوحة | `aichart/api/cron/tradability-calibration`, `economicEventMonitor.ts` | مهام نظام اختيارية في `trading/cron.py` | 4.5 / 6.x | S |
| R17 | **Opportunity scan** | `aichart/src/lib/opportunityScan.ts` | يُدمج في `bots/coordinator.py` كمسح متعدد الإعدادات | 8.1 | S |
| R18 | **UpdateChecker + APK ذاتي الاستضافة** | `aichart/admin_android/UpdateChecker.kt`, `public/admin-android/version.json` | `mokli/mokli/mobile_dist.py` يخدم `/mobile/version.json` + `/mobile/mokli.apk` | 05/M5 | XS |
| R19 | **نمط ApiClient (Bearer + cookie) و RTL theme** | `aichart/admin_flutter/lib/api/client.dart`, `theme.dart` | مرجع فقط لتطبيق React Native (05) — لا ترحيل كود | 05 | — |
| R20 | **Token usage meter** | `foxagent/.../token_usage.py`, `ChatUsageMeter.tsx` | Settings → Overview (04) فوق `llm_usage/` الموجود | — | XS |

### مرفوض صراحة (خارج هدف المنتج)

| الميزة | السبب |
|---|---|
| Billing/Stripe، Pricing، Subscribe، Ads، Support inbox، Admin platform (users/roles) | Mokli منتج مشغّل واحد؛ يعود النظر فيه فقط عند التحول إلى SaaS |
| `admin_flutter` كأساس لتطبيق الجوال | لوحة إدارة (users/billing) لا محادثة؛ نأخذ منها الأنماط فقط (R19) |
| klinecharts canvas (foxagent) | سياسة المستودع: TradingView فقط |
| Claude Agent SDK path (`sdk_runtime.py`) | Mokli متعدد المزودين عبر `providers/` |
| MCP Connectors server (`aichart/mcp/`) | mokli يملك مضيف MCP عاماً؛ يُعاد النظر عند الحاجة لتكامل Claude Desktop |
| Web push VAPID | مُزال في AiChart نفسه؛ نستخدم FCM (05) |
| Semantic memory + pgvector | يتطلب Postgres؛ يبقى SQLite + BoW/Chroma الحالي حتى تظهر حاجة مقاسة |

## 4. ما يُرحَّل إلى الواجهة الجديدة (أنماط، لا نسخ)

الأساس الآن fork من Mokli (04)؛ ما يُنقل هو **السلوك** إلى: قوالب النتائج المنظّمة (`mokli/agent_api/render/templates/`، تُعرض عبر `embeds`)، مسارات Svelte المضافة (`/tasks /recommendations /connect /log`)، ومكوّنات تطبيق React Native (05).

| من | العنصر | إلى |
|---|---|---|
| Mokli | تخطيط الشات، سِكّة المحادثات، إعدادات modal بتبويبات، مُنتقي الموديل | يبقى كما هو في الـ fork (لا ترحيل) |
| AiChart | كارت التوصية، stage checklist، `SmartChartWorkspace` (شات + sidecar) | قوالب `decision`/`plan_status` + Artifacts panel للشارت؛ sidecar لا يُنقل (Artifacts يقوم بدوره) |
| foxagent | `ChatReasoning`، `BotDesk/CircuitBadge/LiveSignals`، `inbox` | Timeline في الـ Pipe (`tool`/`subagent`)، مسار `/tasks` (jobs + approvals)، قالب `risk` (blockers) |
| foxagent | `DeskLayout` RTL-first | مرجع لصفحات Svelte المضافة بالعربية |
| Mokli الحالية | `ArtifactRenderer`, `AgentTraceDrawer`, `TradingTeamPanel`, `tvDrawingAdapter` | `tvDrawingAdapter` يبقى في `chart-host/`؛ البقية تُستبدل بقوالب `render/` وTimeline بعد تنقية النصوص |

## 5. ترتيب التنفيذ داخل هذه الوثيقة

1. R2 (أسرار) و R18 (APK hosting) — صغيرة ومستقلة، تفتح المرحلتين 05 و 7.2.
2. R3 (warehouse) → R1 (backtest) → أداة `fast_backtest`.
3. R4 + R5 + R15 مع بناء مسار `/tasks` في الـ fork و`agent_api/jobs.py` (07 §9).
4. R6 مع Timeline في Pipe Function (07 §4).
5. R7–R11 (الذاكرة/الماكرو) كدفعة واحدة على `intel/`.
6. R12, R13, R16, R17, R20 كتحسينات لاحقة.
7. R14 (Strategy Lab) آخر شيء.
