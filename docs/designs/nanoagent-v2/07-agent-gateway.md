# 07 — بوابة الوكيل (Agent API / Gateway)

> جزء من خطة NanoAgent v2 — انظر [`00-master-plan.md`](./00-master-plan.md)
> قرار المالك (الرسالة 2): `Existing Agent → Agent API / Gateway → REST · SSE · WebSocket · Push → React Native App` و`Agent Gateway → Web Client / iOS / Android → Same Agent`.

---

## 1. الدور والحدود

البوابة طبقة **واحدة** يمر منها كل عميل (Open WebUI fork، تطبيق React Native، تيليجرام لاحقاً عبر أداة `message`). لا يعرف أي عميل شيئاً عن بروتوكول WS الداخلي الحالي (`attach`, `webui_response`, `trading_stream`…) ولا عن `AgentLoop`. الوكيل نفسه واحد ولا يتغيّر: البوابة **تترجم** أحداث `RuntimeEventPublisher` وأدوات التداول إلى عقد عام مستقر.

ما تفعله البوابة:

| الحاجة (من قرار المالك) | كيف تُلبّى |
|---|---|
| الوكيل يعمل في الخلفية | الجلسة تعيش في `AgentLoop` لا في اتصال العميل؛ انقطاع SSE/WS لا يلغي الدور؛ العميل يعود بـ `Last-Event-ID` ويستلم ما فاته من `event_log` |
| مهام/وظائف طويلة | كل دور = `run` بمعرّف؛ الأهداف المستدامة (`session/goal_state.py`) والمهام المجدولة (`cron`) = `jobs` بحالتها وتقدمها |
| Agent Timeline | تدفق أحداث مرتب (`tool_started/tool_finished/subagent_*`) يُخزَّن لكل جلسة ويُعاد بالـ REST |
| حالة الوكيل Working / Waiting / Completed | نموذج حالة واحد مشتق من `TurnRunStatusChanged` + `TurnCompleted` + انتظار الموافقة (§3) |
| Push | مزوّد `nanobot/agent_api/push/` (FCM v1 + APNs) يستهلك نفس الأحداث |
| Approvals | كائن `approval` عام يغلّف `OrderProposal` وأي طلب تأكيد آخر؛ `POST /approvals/{id}` |
| إيقاف مهمة أثناء التنفيذ | `POST /sessions/{id}/cancel` → `AgentLoop._cancel_active_tasks(key)` (loop.py 881) + `jobs/{id}/pause|resume|cancel` |
| أدوات وSubagents | أحداث `tool_*` و`subagent_*` ظاهرة في Timeline بأسمائها وملخص نتائجها (بدون أسرار) |
| Memory | `GET/PUT /memory` (ملاحظات المستخدم، حالات، تفضيلات) فوق `agent/memory.py`؛ لا ذاكرة في العميل |
| Scheduled tasks | `GET/POST/DELETE /jobs` فوق `nanobot/cron/service.py` + goals |
| نتائج منظّمة | `structured` events بأنواع ثابتة (§5): `market`, `analysis`, `scenarios`, `risk`, `decision`, `approval`, `plan_status`, `scorecard` |

ما لا تفعله: لا منطق تداول، لا بوابات، لا قرارات. كل ذلك يبقى في `nanobot/trading/` (القرار الثابت 3 في 00).

---

## 2. المعمارية والملفات

> ملاحظة تسمية: الحزمة `nanobot/gateway/` موجودة أصلاً (إدارة خدمة النظام)، لذا تُنفَّذ البوابة تحت اسم `nanobot/agent_api/`. المسارات العامة تبقى `/api/v2` و`/ws/v2`.
> ملاحظة نقل: HTTP الحالي يمر عبر `websockets.process_request` (لا يدعم التدفق)، لذا البوابة تطبيق aiohttp مستقل على منفذ خاص (`agent_api.port`، افتراضي 8766) داخل **نفس عملية** الـ gateway ويشارك نسخة `AgentLoop` الواحدة؛ ويستضيف أيضاً `/v1/chat/completions` و`/v1/models` (OpenAI-compatible) لربط Open WebUI المباشر.

```
nanobot/agent_api/
├── __init__.py
├── app.py                 # aiohttp sub-app يُركَّب على gateway الحالي تحت /api/v2 و /ws/v2
├── auth.py                # توكنات العملاء (device/web) + نطاقات (scopes)
├── events.py              # GatewayEvent (TypedDict) + المحوّل من RuntimeEvents/stage_events
├── event_log.py           # سجل أحداث لكل جلسة (SQLite، تشذيب حسب العمر) لإعادة التشغيل (Last-Event-ID)
├── state.py               # مشتق حالة الوكيل Working/Waiting/Completed لكل جلسة
├── sessions.py            # ربط session_key ↔ client session id، إنشاء/إدراج/أرشفة
├── jobs.py                # واجهة موحدة فوق cron + goal_state (list/pause/resume/cancel)
├── approvals.py           # مخزن approvals عام (يغلّف mt5_proposals + طلبات تأكيد الأدوات)
├── memory_api.py          # قراءة/تحرير ذاكرة المستخدم
├── labels.py              # GET /labels?locale= من nanobot/trading/locales/*.json
├── routes/
│   ├── sessions.py        # REST + SSE
│   ├── ws.py              # /ws/v2
│   ├── jobs.py
│   ├── approvals.py
│   ├── recommendations.py # الخطة الحية + الأرشيف (فوق recommendations/state_machine)
│   ├── connect.py         # حالة الاتصالات، ملف المخاطرة، Kill Switch، صلاحيات MT5 (08)
│   ├── log.py             # السجل: قرارات، تنفيذ، بوابات، post-mortem
│   ├── settings.py        # التبويبات التسعة (إعادة استخدام settings_* الحالية خلف عقد v2)
│   └── devices.py         # تسجيل أجهزة Push، إقران QR
├── push/
│   ├── base.py            # PushProvider Protocol
│   ├── fcm.py             # FCM HTTP v1 (Android)
│   ├── apns.py            # APNs (iOS)
│   └── router.py          # قرار: WS متصل؟ سلّم فوراً وإلا Push؛ بوابة الصمت (T-9.3)
└── render/
    ├── templates/         # Jinja2 HTML لكل نوع نتيجة منظمة (تُستهلك من Open WebUI embeds)
    └── html.py            # GET /results/{id}/html
```

- تُركَّب على `nanobot/webui/gateway_endpoint.py` الحالي (نفس المنفذ 8765) بدون لمس `agent/loop.py`: البوابة **تشترك** في `RuntimeEventPublisher` وفي `stage_events`/`trace_events` الموجودة، وتستدعي واجهات `AgentLoop` العامة فقط (`submit`, `_cancel_active_tasks` تُغلَّف بدالة عامة `cancel_session(key)`).
- الحلقة الحالية للويب القديم (`/webui`, `/ws`) تبقى حتى القطع (04 §7) ثم تُحذف.
- الأنواع عند الحدود الديناميكية `TypedDict` (`.agent/gotchas.md`)؛ لا `Any` في العقد العام.

---

## 3. نموذج حالة الوكيل

مصدر الحقيقة أحداث موجودة اليوم (`nanobot/bus/runtime_events.py`):

| حدث داخلي | يُترجم إلى |
|---|---|
| `SessionTurnStarted`, `UserInputAccepted`, `TurnRuntimeAdmitted` | `state: working` (`phase: "queued"` → `"thinking"`) |
| `TurnRunStatusChanged(status)` | `state: working` مع `phase` = الحالة النصية (`streaming`, `tool:<name>`, `subagent:<id>`…) |
| approval مُنشأ ولم يُحسم (`approvals.py`) | `state: waiting` مع `waiting_for: {"kind": "approval", "id": ...}` |
| طلب إدخال من أداة (`__event_call__ input` لاحقاً) | `state: waiting` مع `waiting_for: {"kind": "input", ...}` |
| `TurnCompleted` | `state: completed` مع `outcome: ok|cancelled|error` |
| `GoalStateChanged` | تحديث `jobs[]` (goal) لا حالة الجلسة |
| `_cancel_active_tasks` نجح | `state: completed`, `outcome: cancelled` |

القاعدة: الجلسة `waiting` تبقى `waiting` حتى يُحسم الطلب أو ينتهي TTL (`proposal_ttl_seconds` للتنفيذ)؛ عند الانتهاء → `completed` مع `outcome: expired` وحدث `notification`.

---

## 4. عقد الأحداث (SSE و WS)

كل حدث JSON بالشكل:

```json
{"id": "01J...", "session": "s_…", "run": "r_…", "ts": 1727260000123, "kind": "…", "data": {…}}
```

| `kind` | `data` | الاستهلاك |
|---|---|---|
| `delta` | `{text}` | تدفق نص الرد |
| `state` | `{state: working|waiting|completed, phase?, waiting_for?, outcome?}` | شارة الحالة، `status` في Open WebUI |
| `tool` | `{event: started|finished|failed, name, call_id, summary?, duration_ms?}` | Timeline |
| `subagent` | `{event: started|finished, id, role, summary?}` | Timeline (النقاش متعدد الوكلاء) |
| `structured` | `{type, result_id, payload}` — الأنواع في §5 | كروت/تبويبات؛ Open WebUI: `embeds([GET /results/{id}/html])` |
| `artifact` | `{artifact_id, mime, url, title}` | صورة الشارت، ملفات |
| `approval` | `{approval_id, type: execution|modify|close|generic, summary, expires_at, actions: [confirm, cancel]}` | حوار تأكيد / إشعار بأزرار |
| `notification` | `{level, title, body, deep_link}` | Toast / Push |
| `job` | `{job_id, kind: cron|goal, status, progress?, next_run_at?}` | صفحة Tasks |
| `end` | `{run, outcome}` | إغلاق التدفق |

- **SSE**: `GET /api/v2/sessions/{id}/events?after=<event_id>`؛ يُدعم `Last-Event-ID`. الإعادة من `event_log` (احتفاظ افتراضي 7 أيام أو 5000 حدث/جلسة).
- **WS**: `/ws/v2` قناة واحدة لكل عميل، تعدد الجلسات بحقل `session`؛ رسائل العميل: `subscribe`, `unsubscribe`, `send`, `cancel`, `approve`, `ping`. نفس أشكال `data`.
- الترتيب مضمون داخل الجلسة بمعرّف ULID متزايد.
- لا نص عربي ثابت في الأحداث: التسميات تُترجم في العميل عبر `GET /api/v2/labels?locale=`؛ الوكيل نفسه يجيب بلغة `reply_language` (02 §4).

---

## 5. النتائج المنظّمة (حالة الذهب)

الأنواع الثابتة والمصادر الحالية:

| `type` | المصدر | الحقول الأساسية (`payload`) |
|---|---|---|
| `market` | `market_context.py`, `oanda_stream.py`, `news/` | `price, spread, session, dxy, yields, next_event{time, impact}, feed_status` |
| `analysis` | evidence DAG (`evidence/nodes.py`) | `htf_bias, structure, zones[], fvg[], liquidity[], momentum_score, confluence[]` |
| `scenarios` | `node_planner`, T-8.2 | `primary{direction, trigger, invalidation}, alternate{…}, active?` |
| `risk` | `gates/risk_snapshot.py`, `risk_state.py` | `risk_pct, lot, rr, daily_dd_used_pct, open_positions, blockers[]{gate, reason_key}` |
| `decision` | المُركِّب (`decision_contract.md`, 02) | `verdict: buy|sell|wait, entry, stop, targets[], confidence, reasons[], gates_passed[]` |
| `approval` | `mt5_proposals` (+08) | كما في حدث `approval` + `permission_level` |
| `plan_status` | `recommendations/state_machine.py` | `plan_id, state, transitions[], pnl?` |
| `scorecard` | T-6.4 | `period, trades, win_rate, expectancy, max_dd, notes_keys[]` |

- كل نوع له JSON Schema في `nanobot/agent_api/schemas/*.json` وقالب HTML في `render/templates/`؛ الاختبارات تتحقق أن كل حمولة تطابق مخططها وأن القالب لا يحوي نصاً ثابتاً غير مفاتيح تسميات.
- `GET /api/v2/results/{id}` (JSON) و`GET /api/v2/results/{id}/html?locale=` (Open WebUI embeds / WebView احتياطي).
- الوكيل ينتج هذه الأنواع عبر أداة داخلية واحدة `emit_result(type, payload)` تُسجَّل دائماً (D5)، والمُركِّب يستدعيها بدل حشو النص.

---

## 6. REST

جميع المسارات تحت `/api/v2`، Bearer token، JSON، أخطاء `{error: {code, message_key, details}}`.

| المسار | الوظيفة |
|---|---|
| `GET /me` | هوية العميل، النطاقات، `locale` |
| `GET/POST /sessions` · `GET /sessions/{id}` · `DELETE` | إدارة الجلسات (تُطابق `chat_id` في Open WebUI عبر `X-NanoAgent-Session`) |
| `POST /sessions/{id}/messages` | إرسال رسالة (نص/صوت/صورة) → يعيد `run_id` |
| `GET /sessions/{id}/events` (SSE) | التدفق |
| `GET /sessions/{id}/timeline?after=` | Timeline مُخزَّن |
| `POST /sessions/{id}/cancel` | إيقاف الدور الحالي (`cancel_session`) |
| `GET /sessions/{id}/state` | حالة واحدة (لاستطلاع الجوال عند الاستيقاظ) |
| `GET /jobs` · `POST /jobs` · `POST /jobs/{id}/pause|resume|cancel` · `DELETE /jobs/{id}` | cron + goals |
| `GET /approvals?status=pending` · `POST /approvals/{id}` `{decision: confirm|cancel}` | يُنفَّذ عبر `mt5_confirm_order`/`mt5_cancel_order` بنفس بوابات HITL؛ يفحص 08 |
| `GET /recommendations/live` · `GET /recommendations?from=&to=` | الخطة الحية والأرشيف |
| `GET /connect` | حالة OANDA/MetaAPI/TradingView/القنوات + `runtime_state` + ملف المخاطرة + صلاحيات MT5 |
| `PUT /connect/risk-profile` · `PUT /connect/risk/{field}` | 04 §4 |
| `POST /control/kill` · `POST /control/pause` | `runtime_state` (نفس المسار، لا اختصار) |
| `GET/PUT /connect/mt5/permissions` | 08 |
| `GET /log?kinds=&from=` | القرارات، التنفيذ، البوابات، post-mortem، journal (R12) |
| `GET/PUT /memory` | ذاكرة المستخدم (ملاحظات، تفضيلات) |
| `GET /labels?locale=` | كتالوج التسميات |
| `GET /results/{id}` · `GET /results/{id}/html` | §5 |
| `POST /devices` · `DELETE /devices/{id}` · `POST /devices/pair` | Push + إقران QR (05) |
| `GET/PUT /settings/{tab}` | التبويبات التسعة (04 §3.3) |

---

## 7. Push

- `push/router.py`: عند حدث `approval`, `notification`, `structured(decision)`, `job(finished|failed)`: إن كان للمستخدم WS متصل يُسلَّم فوراً فقط؛ وإلا Push إلى كل أجهزته غير الملغاة. بوابة الصمت (T-9.3) تسبق الإرسال.
- الحمولة: `{kind, title_key, body_key, args, session, deep_link, approval_id?}` — لا أسعار ولا مستويات في الحمولة (05 §4)؛ التفاصيل تُجلب بالـ REST بعد الفتح.
- FCM v1 بحساب خدمة، APNs بمفتاح `.p8`؛ الأسرار في `security/secret_store.py` (T-7.2)؛ الإرسال عبر `security/network.py` guards.
- إجراءات الإشعار (تأكيد/إلغاء) تستدعي `POST /approvals/{id}` بتوكن الجهاز؛ التطبيق يفرض بيومترياً قبل الإرسال.

---

## 8. المصادقة والنطاقات

| نوع التوكن | المُصدِر | العمر | النطاقات |
|---|---|---|---|
| `web` | `GET /api/v1/nanoagent/token` من Open WebUI (04 §3.4) | قصير (15 دقيقة، تجديد صامت) | `chat, read, approve, control` |
| `device` | `POST /devices/pair` (QR) | طويل، قابل للإلغاء | `chat, read, approve, control, push` |
| `service` | إعداد يدوي | حسب الحاجة | `read` فقط (لوحات خارجية) |

- `approve` مطلوب لـ `POST /approvals` و`control` لـ `cancel`/`kill-switch`/`pause`/`jobs`.
- إعادة استخدام `nanobot/webui/gateway_tokens.py` للتوقيع؛ إضافة جدول `gateway_clients` (id, kind, scopes, label, created_at, revoked_at).
- الحد الأقصى للطلبات لكل توكن؛ CORS مقصور على أصل Open WebUI.

---

## 9. المهام الطويلة والمجدولة

- **Run**: دور واحد؛ يُلغى بـ `cancel`.
- **Goal**: هدف مستدام (`goal_state.py`) يمتد لأدوار عديدة؛ يظهر كـ `job kind=goal` مع `progress` من `GoalStateChanged`؛ `pause/resume` يعيّنان علماً يفحصه `AgentLoop` قبل كل دور تلقائي.
- **Cron**: `nanobot/cron/service.py`؛ `job kind=cron` مع `next_run_at`؛ التنفيذ يفتح جلسة نظام ويبث أحداثها إلى Timeline الجلسة الأم.
- **خدمة إدارة الصفقات** (T-8.1) تظهر كـ `job kind=goal` دائم اسمه `trade_management` بحالة `working` أثناء وجود صفقات مفتوحة و`waiting` خلافه.
- كل `job` يُعرض في صفحة Tasks (04 §3.2) وفي تبويب Tasks في الجوال (05).

---

## 10. الترتيب والاعتماديات

| الخطوة | المحتوى | يعتمد على |
|---|---|---|
| G1 | `events.py`, `state.py`, `event_log.py` + SSE للجلسات + `cancel` | المرحلة 1 (مسار واحد) |
| G2 | `auth.py`, توكن web/device، `labels.py` | المرحلة 0 (locales JSON) |
| G3 | `structured` + `schemas/` + `render/` + أداة `emit_result` | المرحلة 2 (decision_contract) |
| G4 | `approvals.py` + REST + دمج 08 | 08 |
| G5 | `jobs.py` (cron + goals + trade_management) | T-8.1 |
| G6 | `push/` + `devices` + إقران | G2 |
| G7 | `routes/recommendations|connect|log|settings` | 04 §3–4 |
| G8 | WS `/ws/v2` (بعد استقرار SSE) | G1 |

---

## 11. معايير القبول

- عميل SSE ينقطع 30 ثانية أثناء دور طويل ويعود بـ `Last-Event-ID` فيستلم كل الأحداث الفائتة بالترتيب ولا يفقد `end`.
- `POST /sessions/{id}/cancel` يوقف أداة قيد التنفيذ وsubagent خلال ≤ 2 ثانية ويبث `state: completed/outcome: cancelled`.
- كل نتيجة `structured` تطابق مخططها؛ `GET /results/{id}/html?locale=ar` لا يحوي نصاً ثابتاً خارج الكتالوج (اختبار `rg` على القوالب).
- approval معلّق يجعل الحالة `waiting`؛ التأكيد من الويب أو الجوال يمر بنفس البوابات ويُسجَّل في `/log`؛ انتهاء TTL يبث `expired`.
- لا استيراد من `nanobot/agent_api/` داخل `nanobot/agent/loop.py` أو `runner.py` (اختبار بنية).
- `tests/agent_api/` تعكس بنية الحزمة؛ `basedpyright` نظيف؛ لا `Any` في `events.py`/`schemas`.
