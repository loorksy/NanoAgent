# 05 — تطبيق الجوال (React Native — iOS و Android) بنمط ChatGPT

> جزء من خطة Mokli v2 — انظر [`00-master-plan.md`](./00-master-plan.md)
> قرار المالك (الرسالة 2): `Agent Gateway → REST · SSE · WebSocket · Push → React Native App`؛ الويب و iOS و Android يتحدثون إلى **نفس الوكيل** عبر نفس البوابة ([07](./07-agent-gateway.md)).

---

## 1. المطلوب

- تطبيق React Native لـ **Android (APK/AAB) و iOS** يشبه تطبيق ChatGPT: محادثة، تدفق نصي، صور/شارت، صوت.
- **اتجاهان:** المستخدم يراسل الوكيل، **والوكيل يراسل المستخدم** (توصية، تنبيه أخبار، ضرب وقف، انقطاع تدفق، اقتراح تنفيذ ينتظر التأكيد) حتى والتطبيق مغلق → إشعارات Push.
- أزرار تأكيد/إلغاء (HITL) من داخل الإشعار ومن الكارت، وفق صلاحيات MT5 ([08](./08-mt5-permissions.md)).
- Kill Switch متاح دائماً.
- حالة الوكيل (Working / Waiting / Completed)، Timeline، المهام الطويلة والمجدولة، النتائج المنظّمة — كلها من البوابة بلا منطق خاص بالجوال.

## 2. ما هو موجود اليوم ويمكن الاعتماد عليه

| المكوّن | الحالة | المسار |
|---|---|---|
| قناة WebSocket عامة بإصدار توكن لأي عميل | موجودة، تُستبدل بـ `/ws/v2` و SSE من البوابة | `mokli/channels/websocket/runtime.py` 180–247 |
| عميل بروتوكول TS كامل | موجود؛ يُستبدل بـ `packages/mokli-sdk/` المولَّد من عقد البوابة | `mokli/src/lib/mokli-client.ts`, `packages/client-events/` |
| REST بتوكن Bearer | موجود (`gateway_tokens.py`)؛ يُعاد استخدامه في `agent_api/auth.py` | `mokli/surface/gateway_tokens.py` |
| نسخ صوتي (`transcribe_audio`) | موجود | `mokli/surface/transcription_ws.py` |
| غلاف Android WebView + فحص تحديث + APK ذاتي الاستضافة | موجود في AiChart؛ يُنقل منه `UpdateChecker` + سكربت البناء (R18) | `/tmp/aichart/admin_android/` |
| Push (FCM/APNs) | **غير موجود** في أي مشروع → `mokli/agent_api/push/` (07 §7) | — |

## 3. المعمارية

```
┌─────────────────────────────┐                    ┌──────────────────────────────┐
│ React Native app (Expo)     │  REST /api/v2/*    │ mokli gateway (07)          │
│  iOS + Android              │ ◄────────────────► │  mokli/agent_api/            │
│  packages/mokli-sdk     │  SSE /sessions/…   │   ├ sessions / events / state │
│  (نفس SDK يستعمله Mokli│ ◄────────────────  │   ├ approvals (08)            │
│   Pipe عبر Python نظيره)    │  WS /ws/v2         │   ├ jobs (cron + goals)       │
│                             │ ◄────────────────► │   ├ push/ (FCM v1 + APNs)     │
│  expo-notifications         │ ◄── push ────────  │   └ devices / pairing         │
└─────────────────────────────┘                    └──────────────┬───────────────┘
                                                                  │  Same Agent
                                                          ┌───────▼────────┐
                                                          │ AgentLoop      │
                                                          │ mokli/trading│
                                                          └────────────────┘
```

لا قناة `mobile` منفصلة في `mokli/channels/`: تسجيل الأجهزة، الإقران، Push والإجراءات كلها في البوابة (`agent_api/routes/devices.py`, `agent_api/push/`, `agent_api/approvals.py`) كي لا يتكرر المنطق بين الويب والجوال. أداة `message` و`trading/delivery.broadcast` (T-6.7) تنشر إلى البوابة، والبوابة تقرر WS فوري أم Push.

### 3.1 حزمة SDK مشتركة — `packages/mokli-sdk/`

- TypeScript، تُولَّد أنواعها من `mokli/agent_api/schemas/*.json` (07 §5) وعقد الأحداث (07 §4) بـ `json-schema-to-typescript`؛ اختبار CI يفشل إذا اختلف المولَّد عن الملتزم.
- تحوي: `GatewayClient` (REST + SSE مع `Last-Event-ID` + WS اختياري)، `useSession()`, `useAgentState()`, `useTimeline()`, `useJobs()`, `useApprovals()`؛ مخزن أحداث محلي لإعادة الاتصال.
- تُستهلك من التطبيق ومن أي جزء React/Svelte مستقبلي؛ لا تعتمد على RN (`fetch` + `EventSource` polyfill).

### 3.2 التطبيق — Expo (React Native)

| الجانب | القرار |
|---|---|
| التوجيه | `expo-router` بخمس تبويبات تطابق الويب: Agent, Tasks, Recommendations, Connect, Log |
| الحالة | `zustand` فوق SDK؛ لا منطق تداول في العميل |
| Push | `expo-notifications`: FCM (Android) + APNs (iOS)؛ فئات إشعار بأزرار (`confirm`, `cancel`, `open`) |
| الأمان | `expo-secure-store` لتوكن الجهاز؛ `expo-local-authentication` قبل أي `approve` أو ترقية صلاحية |
| الصوت | `expo-av` تسجيل → `POST /sessions/{id}/messages` بملف صوتي → `transcribe_audio` في الخادم |
| الشارت | صورة `artifact` من الخادم (TradingView فقط، `.agent/design.md`)؛ لا مكتبة شارت محلية |
| النتائج المنظّمة | مكوّن لكل `type` (market, analysis, scenarios, risk, decision, approval, plan_status, scorecard) يقرأ `payload` مباشرة؛ التسميات من `GET /labels?locale=` |
| الخلفية | `expo-background-fetch` لتحديث حالة الجلسات المعلّقة عند الاستيقاظ (`GET /sessions/{id}/state`) |
| التوزيع | EAS Build: APK/AAB موقّع + IPA؛ Android يُستضاف على `/mobile/mokli.apk` + `version.json` (R18) ثم Play internal؛ iOS عبر TestFlight |
| العرض | RTL كامل للعربية (`I18nManager`)، نفس كتالوج التسميات |

### 3.3 الشاشات (MVP)

| الشاشة | المحتوى | مصدر البيانات |
|---|---|---|
| Pairing | مسح QR من Settings → Channels → Devices؛ أو رابط + رمز | `POST /devices/pair` |
| Agent | قائمة جلسات (drawer)، محادثة بتدفق، شارة الحالة Working/Waiting/Completed، Timeline قابل للطي (أدوات، subagents)، كروت النتائج، زر إيقاف أثناء التنفيذ، زر صوت | SSE `/sessions/{id}/events`, `POST /cancel` |
| Tasks | المهام الطويلة والمجدولة: تقدّم، `next_run_at`، إيقاف/متابعة/إلغاء؛ صندوق الموافقات المعلّقة | `GET /jobs`, `GET /approvals?status=pending` |
| Recommendations | الخطة الحية + الأرشيف (كرت `plan_status`) | `GET /recommendations/*` |
| Connect | Kill Switch، إيقاف مؤقت، ملف المخاطرة (المنزلقات السبعة، 04 §4.2)، بطاقة صلاحيات MT5 المختصرة | `GET /connect`, `PUT /connect/*` |
| Log | القرارات، التنفيذ، البوابات، تغييرات الصلاحيات | `GET /log` |
| Notifications inbox | آخر الإشعارات مع أزرار الإجراء | مخزن محلي + `GET /approvals` |

### 3.4 الإشعارات (أنواع + إجراءات)

| النوع (`kind`) | المصدر | الإجراءات في الإشعار |
|---|---|---|
| `approval` | `mt5_propose_order` عند مستوى `propose` (08) | **تأكيد** (بصمة) · إلغاء → `POST /approvals/{id}` |
| `decision` | المُركِّب عند مستوى `execute` (نُفِّذ) أو توصية جاهزة | فتح |
| `plan_status` | `state_machine` (in_trade/tp1/invalidated) | فتح |
| `notification(level=warn)` | هبوط صلاحية تلقائي (08 §4)، `news_shield` (T-4.5)، `feed_disconnected` (T-6.6) | فتح Connect |
| `job(finished|failed)` | cron / goal | فتح Tasks |
| `scorecard` / إحاطة صباحية | T-6.4 / T-6.3 | فتح Log |
| `agent_message` | الوكيل عبر `message` | رد سريع (يفتح المحادثة) |

الحمولة لا تحوي أسعاراً ولا مستويات (07 §7)؛ التطبيق يجلب التفاصيل بعد الفتح.

## 4. الأمان

- توكن الجهاز (نطاقات `chat, read, approve, control, push` — 07 §8) في Keystore/Keychain؛ قابل للإلغاء من Settings → Channels → Devices.
- التأكيد على الاقتراحات ورفع مستوى صلاحيات MT5 يتطلبان بيومترياً محلياً؛ الخادم يفرض TTL والبوابات و08 كالمعتاد.
- Kill Switch من الجوال = `POST /control/kill` (نفس المسار، لا اختصار).
- FCM/APNs عبر `security/network.py` guards ومفاتيح في `secret_store`.

## 5. الترتيب والاعتماديات

| الخطوة | المحتوى | يعتمد على |
|---|---|---|
| M1 | `packages/mokli-sdk/` مولَّد من مخططات البوابة + اختبارات | 07/G1–G3 |
| M2 | تسجيل الأجهزة + إقران QR + Push في البوابة | 07/G6 |
| M3 | تطبيق Expo: Pairing + Agent (تدفق، حالة، Timeline، إيقاف) + إشعارات | M1, M2 |
| M4 | Tasks + Approvals (بصمة) + Recommendations | 07/G4–G5, 08 |
| M5 | Connect (منزلقات، Kill Switch، صلاحيات MT5) + Log | 04 §4, 08 §6 |
| M6 | توزيع: APK ذاتي (`/mobile/version.json`) + TestFlight ثم المتاجر | — |

## 6. معايير القبول

- إقران جهاز بالـ QR خلال أقل من دقيقة؛ الجهاز يظهر في Settings → Channels → Devices.
- رسالة من الويب (Mokli) تظهر على الجوال في نفس الجلسة وبالعكس خلال ثانية؛ الحالة والـ Timeline متطابقان على المنصتين.
- قطع الشبكة 30 ثانية أثناء دور طويل ثم العودة: لا أحداث مفقودة (`Last-Event-ID`).
- زر الإيقاف يلغي أداة قيد التنفيذ ويظهر `completed/cancelled` على الويب والجوال.
- والتطبيق مغلق: توصية → Push خلال ≤ 5 ثوانٍ (Android و iOS)؛ اقتراح → إشعار بأزرار؛ التأكيد بالبصمة ينفّذ عبر HITL ويظهر في Log.
- Kill Switch من الجوال يوقف كل شيء ويُسجَّل.
- اختبارات: `tests/agent_api/test_devices.py`, `test_push.py`, `test_approvals.py`؛ `packages/mokli-sdk` اختبارات وحدات؛ اختبارات RN للـ stores والمكوّنات المنظّمة (snapshot لكل `type`).
