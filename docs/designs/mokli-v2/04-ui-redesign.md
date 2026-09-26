# 04 — الواجهة الرئيسية: Mokli فوق نظام Mokli الحالي

> جزء من خطة Mokli v2 — انظر [`00-master-plan.md`](./00-master-plan.md)
> **قرار المالك (2026-09-25):** استخدام واجهة Mokli كعميل الويب الرئيسي، مع الإبقاء على ملفات نظام Mokli (الوكيل، الأدوات، البوابات، القنوات، الإعدادات) كما هي خلف **Agent Gateway** واحد ([07](./07-agent-gateway.md)).

---

## 1. المعمارية

```
Existing Agent (mokli AgentLoop + tools + gates + memory)
        │
        ▼
Agent Gateway  (mokli/agent_api/)        ← 07
        ├── REST     /api/v2/*
        ├── SSE      /api/v2/sessions/{id}/events
        ├── WebSocket /ws/v2
        └── Push     FCM / APNs
        │
        ├──────────────► Mokli (fork: loorksy/mokli-mokli)   = Web Client
        │                  ├ Pipe Function "mokli"  (Python داخل Mokli backend)
        │                  │    يترجم أحداث الـ Gateway → status / embeds / confirmation / notification
        │                  └ Svelte routes مضافة: /tasks /recommendations /connect /log + إعدادات مخصصة
        │
        └──────────────► React Native App (iOS + Android)             = Same Agent  ← 05
```

**ما يُستبدل:** `mokli/` (React SPA) بالكامل، بعد القطع.
**ما يبقى بلا تغيير:** كل `mokli/` عدا إضافة `mokli/agent_api/` وتعديلات صغيرة في `mokli/mokli/*` لإعادة استخدام معالجات الإعدادات/التداول من الـ Gateway.

## 2. لماذا هذا الشكل يعمل الآن (وقيوده)

| احتياج | آلية Mokli | القيد وحلّه |
|---|---|---|
| تدفق النص | Pipe يُنتج `yield` من SSE الـ Gateway | — |
| حالة الوكيل Working / Waiting / Completed | `__event_emitter__({"type":"status", ...})` سجل حالات لكل رسالة | نُظهر أيضاً شريط حالة دائم في الـ fork يستهلك WS |
| Agent Timeline (أدوات، subagents، مراحل) | `status` متسلسلة + كتلة `<details>` قابلة للطي في الرسالة | Timeline كامل في صفحة `/log` (Svelte + WS) |
| نتائج منظمة (Market / Analysis / Scenarios / Risk / Decision) | `embeds` (Rich UI HTML مستمر) + لوحة **Artifacts** يمين الشات | HTML يُولَّد في Mokli (`mokli/agent_api/render/`) لا في Pipe؛ iframe محكوم بـ `IFRAME_CSP` |
| شارت TradingView | `embeds` iframe إلى `https://<gateway>/chart-host?token=…` (المكتبة مستضافة عندنا كما اليوم) | يبقى `chart-host/` + `TvChart` الحالي كصفحة مستقلة تُضمَّن |
| موافقات (Approvals / HITL) | `__event_call__({"type":"confirmation"})` يوقف التنفيذ حتى OK/Cancel | التأكيد يمرّ للـ Gateway `POST /approvals/{id}` — نفس بوابات HITL؛ في الجوال عبر إشعار |
| إشعارات داخل الواجهة | `notification` toast | Push خارج المتصفح عبر قناة `mobile`/Web Push (07) |
| إيقاف مهمة أثناء التنفيذ | زر Stop في Mokli يلغي الطلب → Pipe يلتقط الإلغاء ويستدعي `POST /sessions/{id}/cancel` | Tasks طويلة تُلغى من صفحة `/tasks` |
| Memory | Mokli Memory **معطّل**؛ الذاكرة في Mokli (`memory/`, Dream) وتُعرض في `/log` | لا ازدواجية |
| هوية الجلسة | `__metadata__["chat_id"]` → header `X-Mokli-Session` | جلسة Mokli = جلسة mokli 1:1 |
| العلامة التجارية | مسموح تغييرها لنشر ≤ 50 مستخدماً/30 يوماً (رخصة v0.6.6+) | إذا تجاوزنا 50 مستخدماً: نبقي «Mokli» أو ترخيص Enterprise — يُوثَّق في README |

## 3. الـ fork: ما يُضاف وما يُخفى

### 3.1 Pipe Function (`mokli_pipe.py`) — يُثبَّت من Admin → Functions

```
class Pipe:
    Valves: gateway_url, gateway_token, default_locale, show_timeline
    async def pipe(body, __user__, __metadata__, __event_emitter__, __event_call__):
        session = __metadata__["chat_id"]
        async for ev in gateway.stream(session, body["messages"][-1], locale):
            match ev.kind:
              "delta"        → yield ev.text
              "state"        → status(description=label(ev.state), done=ev.state=="completed")
              "tool"         → status("⚙ " + label(ev.tool)) ; append to <details> timeline
              "structured"   → embeds([gateway.render(ev.result_id)], replace=True)   # Market/Analysis/…
              "artifact"     → files([...]) or embeds
              "approval"     → ok = event_call(confirmation) → gateway.resolve(ev.approval_id, ok)
              "notification" → notification(...)
              "end"          → status(done=True)
```

Pipe لا يحوي منطقاً تداولياً ولا نصوصاً؛ التسميات تأتي من `GET /api/v2/labels?locale=`.

### 3.2 مسارات Svelte مضافة (`src/routes/(app)/…`)

| القسم | المسار | المصدر | API |
|---|---|---|---|
| **Agent** | `/` (شات Mokli الأصلي) | كما هو + شريط حالة الوكيل والسعر في `Navbar` | Pipe + `GET /api/v2/agent/state` (WS) |
| **Tasks** | `/tasks` | جديد | `GET/POST /api/v2/tasks`, `POST /tasks/{id}/cancel|pause|resume`, Approvals المعلقة |
| **التوصيات** | `/recommendations` | جديد | `GET /api/v2/recommendations?status=live|archived`, تفاصيل + نتائج منظمة |
| **الربط** | `/connect` | جديد | `GET /api/v2/connections`, `POST /connect/{broker|feed}`, `POST /control/{kill|pause|mode}`, `GET/POST /api/v2/risk/profile` |
| **السجل** | `/log` | جديد | `GET /api/v2/timeline?kinds=…` (تنفيذات، انتقالات، تنبيهات، تقارير، أثر الوكيل) |

الشريط الجانبي: الأقسام الخمسة أعلى قائمة المحادثات؛ يُخفى Workspace (Models/Knowledge/Prompts/Tools)، Notes، Playground، Channels الخاصة بـ Mokli، ولوحة Admin إلا للمشغّل.

### 3.3 الإعدادات (نبدّل تبويبات Settings modal)

| التبويب | المصدر | API |
|---|---|---|
| Overview | جديد | `GET /api/v2/settings/overview` (توكنات، حالة) |
| Appearance | Mokli «Interface» + اللغة (ar/en، RTL) | محلي |
| Models | جديد (يستبدل «Connections») | `GET/POST /api/v2/settings/models` — يلفّ `mokli/mokli/settings_models.py` |
| Channels | جديد | Telegram token، WhatsApp QR، **Mobile devices** (إقران QR، إلغاء) |
| Capabilities | جديد | صورة/صوت/ويب/Dream + مهارات التداول |
| System | جديد | منطقة زمنية، خدمة API، إعادة تشغيل، تشخيص |
| Advanced | جديد | إعادة المحاولة، حدود الأدوات، sandbox، SSRF |
| About | Mokli + إصدار Mokli | `GET /api/v2/version` |
| **Risk Parameters** | جديد | نفس مكوّن المنزلقات في `/connect` + أكورديون «متقدم» |

تبويبات Mokli الأصلية Personalization/Audio/Chats/Account تُدمج (الصوت داخل Capabilities) أو تُخفى.

### 3.4 المصادقة

- مشغّل واحد: Mokli بحساب admin واحد؛ Pipe يحمل توكن Gateway طويل الأجل في Valves (مشفّر في DB الخاصة بـ Mokli).
- صفحات Svelte المضافة تستدعي الـ Gateway بتوكن قصير الأجل يصدره Mokli backend عبر endpoint وسيط `GET /api/v1/mokli/token` (يتحقق من جلسة Mokli ثم يطلب توكن من الـ Gateway) — لا يصل توكن الـ Gateway الطويل إلى المتصفح.

## 4. تبسيط الربط وملف المخاطرة (المواصفة مستقلة عن التقنية)

### 4.1 ملفات المخاطرة

| الملف | risk/trade | daily loss | max trades | min R:R | news caution | cooldown | spread tol. |
|---|---|---|---|---|---|---|---|
| محافظ | 0.5% | 2% | 1 | 2.5 | 30 min | 4 h | 45 pts |
| متوازن (افتراضي) | 1.0% | 3% | 2 | 2.0 | 15 min | 3 h | 60 pts |
| هجومي | 2.0% | 5% | 3 | 1.5 | 10 min | 2 h | 80 pts |

### 4.2 المنزلقات السبعة والمشتقات

| المنزلق | الحقل الأساسي | المدى/الخطوة | مشتقات تختفي من الواجهة |
|---|---|---|---|
| المخاطرة لكل صفقة % | `risk_pct_default` | 0.25–3 / 0.25 | `risk_pct_max = ×2`, `risk_pct_news_day = ×0.5` |
| حد الخسارة اليومي % | `daily_drawdown_pct` | 1–6 / 0.5 | `equity_spike_pct = ×0.67` |
| أقصى صفقات مفتوحة | `max_open_gold_positions` | 1–4 stepper | `max_total_lots` (T-3.5) |
| أدنى R:R | `min_rr` | 1.5–3 / 0.25 | `min_rr_live_fill = −0.5`, `breakeven_rr = 1.0` |
| حذر الأخبار (دقائق) | `news_shield_minutes` | 5–45 / 5 | `pre_news_freeze = ×1.5`, `blackout_before = ×2`, `blackout_after = ×1`, `post_news_entry_wait = ×1`, `spread_pre_news_minutes = ×0.2` |
| التهدئة بعد الخسائر (ساعات) | `cooldown_after_two_losses_minutes` | 1–6 h / 0.5 | `session_minutes = ÷3`, `after_news_stop = ÷4`, `consecutive_losses = 2` |
| تحمّل السبريد (نقاط) | `spread_max_points` | 30–120 / 5 | `spread_multiplier_pre_news = 3`, `flat_near_entry_points = ×0.5` |

### 4.3 المفاتيح الخمسة

درع الأخبار (`news_shield`+`early_exit`) · قاطع الخسارة اليومي · قفل التهدئة · حارس السبريد · أقفال الجلسة والعطل (`session_lock`+`holiday_lock`). `rr_filter` و`max_positions` دائمَا التفعيل (يُعطَّلان من «متقدم» فقط).

### 4.4 لوحة التحكم في `/connect`

| العنصر | النوع | الخلفية |
|---|---|---|
| Kill Switch | زر أحمر «اسحب للتأكيد» | `POST /api/v2/control/kill` → `runtime_state.kill_switch` + flatten HITL |
| صلاحيات الوكيل على MT5 | بطاقة تعرض المستوى الحالي (توصية / اقتراح / تنفيذ) وحدوده + زر «تعديل» | [08](./08-mt5-permissions.md) |
| إيقاف مؤقت | مفتاح | `POST /api/v2/control/pause` |

### 4.5 بطاقات الاتصال

| البطاقة | الحالة | الزر |
|---|---|---|
| تدفق الأسعار (OANDA) | متصل/منقطع، آخر تيك، سبريد | إعداد |
| الوسيط MT5 (MetaAPI) | متصل/غير مهيأ، الرصيد، الهامش، **مستوى الصلاحية** | ربط / صلاحيات |
| Telegram · WhatsApp · Mobile | مفعّل/مقترن، عدد الأجهزة | Settings → Channels |

### 4.6 مصير بقية الحقول (~50)

| المجموعة | القرار |
|---|---|
| ثوابت المحرك (`midnight_spread_*`, `rollover_*`, `daily_close_*`, `news_void_seconds`, `first_minute_dead`, `ping_max_ms`, `exec_latency_max_ms`, `slippage_probe_points`, `lot_dual_check_*`, `news_candle_volume_z`, `g7_max_slippage_atr`, `liquidity_proximity_atr`, `entry_max_atr_distance`, `target_max_atr_distance`, `half_distance_pct`, `max_reprice_rounds`, `stale_quote_seconds`, `disconnect_alert_seconds`, `margin_min_pct`) | تختفي من الواجهة؛ `config.json` فقط |
| إدارة الصفقة (`partial_tp*`, `profit_lock_*`, `trail_atr_mult`, `*_sl_buffer_points`, `time_stop_hours`) | Risk Parameters → متقدم / إدارة الصفقة (منزلقات) |
| التنفيذ (`proposal_ttl_seconds`, `max_confirm_slippage_points`, `slippage_max_points`) | متقدم / التنفيذ |
| التقلب (`adr_chase_multiple`, `gap_no_chase_points`, `news_candle_*`, `atr_double_lot_halve`, `emergency_move_points_per_minute`, `bad_tick_points`) | متقدم / التقلب |
| المعلّق (`idea_stale_hours`, `pending_ttl_hours`) | متقدم / الأوامر المعلقة |

### 4.7 الخلفية

| الملف | التغيير |
|---|---|
| `mokli/config/schema.py` | `risk_profile`, `max_total_lots` |
| `mokli/trading/risk_profiles.py` (جديد) | جداول الملفات + `derive_parameters()` + اختبار خصائص |
| `mokli/agent_api/routes/risk.py` | `GET/POST /api/v2/risk/profile` يلفّ `trading_risk_api.py`؛ `RISK_FIELD_SPECS.tier: primary|advanced|hidden` |

## 5. النتائج المنظمة في الواجهة

كل نتيجة `structured` من الـ Gateway لها قالب HTML في `mokli/agent_api/render/templates/` (Jinja2، RTL-aware، بدون JS خارجي) يُرسل كـ `embeds`. أنواع الذهب: `market`, `analysis`, `scenarios`, `risk`, `decision`, `approval`, `plan_status`, `scorecard` — المخطط في [07 §5](./07-agent-gateway.md).

## 6. النصوص واللغة

- لا نص عربي في Pipe ولا في Svelte المضاف؛ التسميات من `GET /api/v2/labels?locale=` (مصدرها `mokli/trading/locales/*.json`) ومن `src/lib/i18n/locales/{ar,en}/mokli.json` في الـ fork لنصوص الصفحات المضافة.
- RTL عند `ar` عبر آلية Mokli الحالية.

## 7. الترحيل والقطع

1. بناء `mokli/agent_api/` (07) — يعمل بالتوازي مع `mokli/` الحالية.
2. Fork `mokli-ui/mokli-ui` → `loorksy/mokli-mokli`؛ تثبيت Pipe؛ تشغيل الشات فقط ضد الـ Gateway (Docker بجوار mokli).
3. إضافة المسارات الخمسة والإعدادات؛ اختبارات Vitest/Playwright في الـ fork.
4. تشغيل مزدوج على `mokli.lork.cloud` (`/` → Mokli، `/legacy` → React) لدورة تحقق.
5. القطع: عميل React حُذف. `mokli/public/charting_library/` و`chart-host/` يبقيان حتى لا تتوقف الرسوم. `hatch_build.py` لا يجمّع الواجهة القديمة. البوابة لا تقدّم الـ SPA.
6. سياسة upstream: rebase شهري على tag مستقر من Mokli؛ كل تعديلاتنا في ملفات مضافة أو ملفات قليلة موثّقة في `FORK_NOTES.md`.
