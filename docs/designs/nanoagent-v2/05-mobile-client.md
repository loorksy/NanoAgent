# 05 — تطبيق الجوال (Android APK) بنمط ChatGPT

> جزء من خطة NanoAgent v2 — انظر [`00-master-plan.md`](./00-master-plan.md)

---

## 1. المطلوب

- تطبيق Android (APK قابل للتحميل من المنصة، ولاحقاً Play) يشبه تطبيق ChatGPT: محادثة، تدفق نصي، صور/شارت، صوت.
- **اتجاهان:** المستخدم يراسل الوكيل، **والوكيل يراسل المستخدم** (توصية، تنبيه أخبار، ضرب وقف، انقطاع تدفق، اقتراح تنفيذ ينتظر التأكيد) حتى والتطبيق مغلق → إشعارات Push.
- أزرار تأكيد/إلغاء (HITL) من داخل الإشعار ومن الكارت.
- Kill Switch متاح دائماً.

## 2. ما هو موجود اليوم ويمكن الاعتماد عليه

| المكوّن | الحالة | المسار |
|---|---|---|
| قناة WebSocket عامة بإصدار توكن لأي عميل | موجودة (`token_issue_path` / `token_issue_secret`) | `nanobot/channels/websocket/runtime.py` 180–247 |
| عميل بروتوكول TS كامل (attach, message, delta, stream_end, trading_stream, goal_state, webui_response …) | موجود | `webui/src/lib/nanobot-client.ts`, `webui/src/lib/types.ts`, `packages/client-events/notifications.ts` |
| REST بتوكن Bearer لكل `/api/*` | موجود | `nanobot/webui/gateway_tokens.py`, `ws_http.py` |
| نسخ صوتي (`transcribe_audio`) | موجود | `nanobot/webui/transcription_ws.py` |
| PWA أساسية | `manifest.json` + `sw.js` بدون push | `webui/public/` |
| غلاف Android WebView + فحص تحديث + APK ذاتي الاستضافة | موجود في AiChart | `/tmp/aichart/admin_android/` (`MainActivity.kt`, `UpdateChecker.kt`, `infra/build-admin-android.sh`) |
| Push (FCM/APNs/Web Push) | **غير موجود** في NanoAgent ولا في AiChart/foxagent | — |

## 3. المعمارية المقترحة

```
┌──────────────────────┐   WSS (nanobot protocol)   ┌────────────────────────────┐
│  Android app         │ ◄────────────────────────► │ nanobot gateway            │
│  (Expo / React Native│   REST Bearer /api/*        │  channels/websocket        │
│   + shared TS client)│ ◄────────────────────────► │  channels/mobile  (جديد)   │
│                      │                             │   ├ device registry        │
│  FCM SDK             │ ◄── push (FCM HTTP v1) ───  │   ├ push sender (FCM v1)   │
└──────────────────────┘                             │   └ action endpoints       │
                                                     └────────────────────────────┘
```

### 3.1 الخلفية: قناة `mobile` جديدة (`nanobot/channels/mobile/`)

تُبنى كحزمة قناة قياسية (auto-discovery عبر `pkgutil` كبقية القنوات) — لا تغيير في `agent/loop.py`.

| الملف | الدور |
|---|---|
| `manifest.py` | تعريف القناة `mobile`، الإعدادات: `fcm_service_account_path`, `pairing_ttl_seconds`, `max_devices` |
| `runtime.py` | يستقبل `OutboundMessage` الموجهة للقناة `mobile` → إن كان الجهاز متصلاً بالـ WS يُسلَّم فوراً؛ وإلا Push |
| `devices.py` | SQLite `mobile_devices` (device_id, fcm_token, platform, label, paired_at, last_seen, revoked) — `TypedDict` عند الحد |
| `pairing.py` | إقران بـ QR: الويب يولّد `pairing_code` (TTL 5 دقائق) → التطبيق يمسحه → `POST /api/mobile/pair` يعيد `device_token` طويل الأجل + عنوان WS + `token_issue_path` |
| `push.py` | إرسال FCM HTTP v1 (حساب خدمة) — عبر `security/network.py` guards؛ payload: `{kind, title, body, session_key, artifact_id?, proposal_id?, actions[]}` |
| `actions.py` | `POST /api/mobile/actions/{proposal_id}/confirm|cancel` و`/api/mobile/kill-switch` — تُعيد استخدام `mt5_confirm_order` / `runtime_state` بنفس فحوص HITL |

كيف يراسل الوكيل المستخدم: أداة `message` الحالية تدعم `channel=` ؛ `trading/delivery.py::broadcast` (T-6.7) تُرسل إلى كل القنوات المفعّلة بما فيها `mobile`. الإشعارات الاستباقية تمرّ عبر بوابة الصمت (T-9.3) قبل الإرسال.

### 3.2 التطبيق: Expo (React Native) — **الموصى به**

| السبب | التفصيل |
|---|---|
| مشاركة الكود | `packages/client-events` و`nanobot-client.ts` TypeScript؛ يُنقلان إلى `packages/nanobot-protocol/` ويُستهلكان من الويب والجوال معاً — بروتوكول واحد، أنواع واحدة |
| نفس فريق React | مكونات الكارت/الـ artifacts تُعاد كتابتها بـ RN مع نفس البنية |
| Push | `expo-notifications` + FCM (Android) وAPNs لاحقاً (iOS بدون كود إضافي في الخادم سوى مزوّد) |
| توزيع | EAS Build يُنتج APK/AAB موقّعاً؛ الملف يُستضاف على `/mobile/nanoagent.apk` + `version.json` (نفس نمط `UpdateChecker.kt` في AiChart) |

**البديل السريع (مرحلة 0):** غلاف WebView مثل `admin_android` يحمّل `https://nanoagent.lork.cloud/#/agent` + FCM للإشعارات فقط. يُنجز خلال جلسة عمل واحدة تقريباً ويُستبدل بالتطبيق الأصلي لاحقاً؛ عيبه: لا عمل بدون شبكة، وتجربة التمرير/لوحة المفاتيح أضعف.

### 3.3 شاشات التطبيق (MVP)

| الشاشة | المحتوى |
|---|---|
| Pairing | مسح QR من Settings → Channels → Mobile؛ أو إدخال رابط + رمز |
| Agent (رئيسية) | قائمة محادثات (drawer)، محادثة بتدفق، كارت التوصية، صورة الشارت، زر صوت (يرسل `transcribe_audio`)، شريط حالة السعر/التدفق |
| Recommendations | الخطة الحية + الأرشيف (نفس API الويب) |
| Tasks | قراءة + إيقاف/تشغيل |
| Connect (مختصر) | Kill Switch، وضع التشغيل، ملف المخاطرة (المنزلقات السبعة) |
| Notifications inbox | آخر الإشعارات مع أزرار الإجراء |

### 3.4 الإشعارات (أنواع + إجراءات)

| النوع | المصدر | الإجراءات في الإشعار |
|---|---|---|
| `recommendation_ready` | `run_trading_kernel` | فتح، تجاهل |
| `proposal_pending` | `mt5_propose_order` | **تأكيد**، إلغاء (تنفّذ عبر `actions.py` مع نفس بوابات HITL؛ التأكيد يطلب بصمة/قفل الجهاز) |
| `plan_transition` | `state_machine` (in_trade/tp1/invalidated) | فتح |
| `news_shield` | T-4.5 | فتح |
| `feed_disconnected` | T-6.6 | فتح Connect |
| `morning_briefing` / `scorecard` | T-6.3 / T-6.4 | فتح Log |
| `agent_message` | الوكيل عبر `message` | رد سريع (يفتح المحادثة) |

## 4. الأمان

- توكن الجهاز طويل الأجل يُخزَّن في Android Keystore (`expo-secure-store`)؛ قابل للإلغاء من Settings → Channels → Mobile.
- التأكيد على الاقتراحات من الإشعار يتطلب مصادقة بيومترية محلية + التوكن؛ الخادم يفرض `proposal_ttl_seconds` والبوابات كالمعتاد.
- Kill Switch من الجوال = نفس المسار `runtime_state.kill_switch` (لا مسار مختصر).
- FCM payload لا يحوي أسعاراً أو مستويات حساسة إلا العنوان؛ التفاصيل تُجلب بعد الفتح عبر REST بالتوكن.
- إرسال FCM يمرّ عبر `validate_url_target` (SSRF policy) ومهلة زمنية.

## 5. الترتيب والاعتماديات

| الخطوة | يعتمد على |
|---|---|
| M0 غلاف WebView + FCM إشعارات فقط (اختياري للتسليم السريع) | قناة `mobile` (devices + push) |
| M1 `packages/nanobot-protocol` مشترك | تنظيف `nanobot-client.ts` |
| M2 قناة `mobile` كاملة (pairing, push, actions) + اختبارات | T-6.7 broadcast |
| M3 تطبيق Expo: Pairing + Agent + إشعارات | M1, M2 |
| M4 Recommendations + Tasks + Connect + Kill Switch | 04 (APIs المبسطة) |
| M5 توزيع APK ذاتي (`/mobile/version.json`) ثم Play internal track | — |

## 6. معايير القبول

- إقران جهاز بالـ QR خلال أقل من دقيقة؛ الجهاز يظهر في Settings → Channels → Mobile.
- رسالة من الويب تظهر على الجوال (نفس الجلسة) وبالعكس خلال ثانية.
- والتطبيق مغلق: إصدار توصية → إشعار FCM خلال ≤ 5 ثوانٍ؛ اقتراح تنفيذ → إشعار بأزرار؛ التأكيد من الإشعار ينفّذ عبر HITL ويظهر في Log.
- Kill Switch من الجوال يوقف كل شيء ويُسجَّل.
- اختبارات: `tests/channels/mobile/` (pairing, push payload, action HITL, revoke) + اختبارات RN للـ stores.
