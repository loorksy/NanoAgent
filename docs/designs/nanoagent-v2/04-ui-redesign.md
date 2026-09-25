# 04 — الواجهة الجديدة (WebUI v2)

> جزء من خطة NanoAgent v2 — انظر [`00-master-plan.md`](./00-master-plan.md)

---

## 1. قرار الأساس: Open WebUI أم واجهة جديدة بملفات جديدة؟

### الحقائق التي تحكم القرار

| العامل | Open WebUI | واجهة NanoAgent الحالية |
|---|---|---|
| التقنية | SvelteKit + FastAPI (Python) خاص بها | React 18 + Vite + TypeScript + Tailwind + shadcn/Radix |
| بروتوكول المحادثة | OpenAI-compatible `/v1/chat/completions` (SSE) + Sockets خاصة | WebSocket multiplex خاص (`nanobot-client.ts`, ~30 نوع حدث: `delta`, `trading_stream`, `goal_state`, `webui_response` …) |
| الرخصة | BSD-3 + **بند العلامة التجارية (v0.6.6+)**: لا يجوز إزالة/تغيير علامة «Open WebUI» في أي نشر يتجاوز 50 مستخدماً خلال 30 يوماً إلا بترخيص Enterprise أو إذن كتابي ([license](https://docs.openwebui.com/license/)) | MIT (nanobot) |
| ما نحتاجه ولا يوجد فيه | TradingView `charting_library` widget + drawing adapter، كروت توصية بحالة، stage checklist، HITL confirm، artifacts، Tasks/Log/Connect | موجود (≈22 مكوّناً تحت `webui/src/components/trading/`) |
| RTL/عربية | مدعوم | مدعوم (`i18n/locales/ar/common.json` 2017 سطراً + `dir=rtl`) |

### الخيار A — Fork Open WebUI كواجهة رئيسية (ممكن، غير موصى به)

المسار التقني إن أُصرّ عليه:

1. نشر NanoAgent كـ «موديل» عبر `nanobot/api/server.py` (`/v1/chat/completions`, `/v1/models`) — موجود.
2. تمديد الـ SSE بحقول غير قياسية (`x_nanoagent: {stage, artifact, proposal}`) وكتابة **Svelte components** جديدة لرسمها داخل رسائل Open WebUI.
3. صفحات Svelte جديدة: Tasks, Recommendations, Connect, Log — تتصل مباشرة بـ `/api/trading/*` و`/api/settings/*` (توكن Bearer).
4. حذف/إخفاء: Workspace (models/knowledge/prompts/tools)، Admin panel، Pipelines، Notes، Playground.
5. إعادة كتابة TradingView sidecar و`tvDatafeed`/`tvDrawingAdapter` بـ Svelte.
6. مزامنة مستمرة مع upstream سريع الإصدار (إصدار كل أسبوع تقريباً) مع تعارضات دائمة في الملفات المعدّلة.

**التكلفة:** إعادة كتابة كل مكونات التداول من React إلى Svelte، بروتوكولان (SSE للنص، WS للأحداث)، وقيد رخصة على العلامة التجارية عند التوسع. **المكسب الوحيد:** الشكل المألوف لواجهة الشات — وهو قابل للنسخ بدون الكود.

### الخيار B — واجهة جديدة بملفات جديدة بلغة تصميم Open WebUI (**الموصى به**)

- حزمة React جديدة داخل نفس مشروع Vite (نفس pipeline البناء إلى `nanobot/web/dist`): **`webui/src/app/`** — لا يُعاد استخدام أي ملف من `webui/src/App.tsx` (3099 سطراً) أو `Sidebar.tsx` أو `components/settings/*` (تُحذف عند الانتهاء).
- يُعاد استخدام (نسخاً ثم تنقية) فقط: `components/ui/*` (shadcn)، `lib/nanobot-client.ts` (البروتوكول)، `lib/chart/tv/*`، `components/trading/{TvChart,ChartTradeOverlay,TradingRecommendationCard,ArtifactRenderer,TradingStageChecklist,TradingTeamPanel,AgentTraceDrawer}.tsx` — بعد نقل النصوص الثنائية إلى i18n.
- لغة التصميم: تخطيط Open WebUI (سِكّة يسارية قابلة للطي للمحادثات، منطقة محادثة مركزية بعرض محدود، مُنتقي الموديل في الشريط العلوي، إعدادات كـ **modal** بتبويبات يسارية) + من AiChart (كارت التوصية، sidecar الشارت، checklist المراحل) + من foxagent (`ChatReasoning` خط زمني حي للوكلاء، Desk layout، RTL-first).

**القرار المعتمد في هذه الخطة: الخيار B.** إن قرر المالك الخيار A لاحقاً، فالقسم 3–5 أدناه (الأقسام، الحقول، المنزلقات) يبقى صالحاً كمواصفة بغض النظر عن التقنية.

---

## 2. بنية الملفات الجديدة

```
webui/src/app/
  main.tsx                    # نقطة الدخول الجديدة (يستبدل src/main.tsx عند القطع)
  router.tsx                  # hash router بسيط: #/agent, #/tasks, #/recommendations, #/connect, #/log, #/settings/<tab>
  shell/
    AppShell.tsx              # سِكّة + محتوى + sidecar
    Rail.tsx                  # الأقسام الخمسة + المحادثات + زر الإعدادات
    TopBar.tsx                # الموديل، حالة الاتصال، Kill Switch السريع، اللغة
    SidecarChart.tsx          # TradingView (desktop) / BottomSheet (mobile)
  features/
    agent/                    # المحادثة: Thread, Composer, MessageList, LiveTeamTimeline, ProposalCard(HITL)
    tasks/                    # TasksBoard, TaskCard, TaskEditor
    recommendations/          # RecommendationsList, RecommendationDetail, OutcomeBadge
    connect/                  # ConnectionsGrid, ControlPanel, RiskProfileSliders
    log/                      # ActivityLog, ExecutionsLog, ReportsList, AgentTrace
    settings/                 # SettingsModal + tabs/{Overview,Appearance,Models,Channels,Capabilities,System,Advanced,About,RiskParameters}.tsx
  state/                      # stores (zustand أو React context): session, trading, settings, connection
  api/                        # trading.ts, settings.ts, tasks.ts (REST) + ws.ts (nanobot-client)
  i18n/                       # ar.json, en.json — كل النصوص هنا (لا نص ثابت في TSX)
```

قواعد إلزامية للكود الجديد: لا نص واجهة داخل TSX (كل شيء عبر `t()`)، RTL افتراضي عند `ar`، لا `console.log`، اختبار Vitest لكل feature، لا استيراد من `webui/src/components/*` القديمة إلا من قائمة الترحيل أعلاه.

---

## 3. الأقسام الرئيسية (خمسة فقط)

| القسم | المسار | المحتوى | يحل محل |
|---|---|---|---|
| **Agent** | `#/agent`, `#/agent/<session>` | محادثة الوكيل الواحد + sidecar الشارت + خط زمني حي للفريق عند تشغيل `run_trading_team` + كارت HITL (تأكيد/إلغاء) داخل الرسالة | `#/chat`, `#/chart`, `#/briefing` (الإحاطة تصبح artifact في المحادثة/Log) |
| **Tasks** | `#/tasks` | كل ما يعمل لاحقاً أو باستمرار: مهام مجدولة (cron)، أهداف مستدامة (`create_goal`)، مراقبات («خبرني إذا…»)، خدمة إدارة الصفقات، السيناريوهات المشروطة (T-8.2)، الاقتراحات المنتظرة للتأكيد | `settings?section=automations`, goals panel |
| **التوصيات** | `#/recommendations` | الخطة الحية + المؤرشفة (win/loss/expired/superseded) مع كارت التوصية، الشارت المرسوم، تقرير البوابات بالتسميات العامة، نتيجة المتابعة | `#/recommendations`, `#/inbox` |
| **الربط** | `#/connect` | بطاقات حالة الاتصالات + لوحة التحكم (Kill Switch, Pause, Paper/Live, وضع الاستقلالية) + **ملف المخاطرة بالمنزلقات** (القسم 5) | `#/connect`, `#/channels` |
| **السجل** | `#/log` | خط زمني موحّد: تنفيذات MT5، انتقالات الخطط، تنبيهات، تقارير الأداء (T-6.4)، الإحاطة الصباحية، أثر الوكيل (trace) لكل دور، سجلات النظام | `#/performance`, `AgentTraceDrawer`, System logs |

الشريط العلوي يحوي دائماً: حالة تدفق الأسعار (أخضر/أحمر)، السبريد الحالي، زر **Kill Switch** بتأكيد مزدوج.

---

## 4. الإعدادات (modal بتبويبات)

| التبويب | يبقى/يتغير | المحتوى |
|---|---|---|
| Overview | يبقى | استهلاك التوكنات، الحالة العامة، روابط سريعة |
| Appearance | يبقى | الثيم، اللغة (ar/en)، كثافة العرض، إشعارات المتصفح |
| Models | يبقى | الموديل النشط، المزودون (BYOK)، معاملات التوليد، fallback |
| Channels | **يتغير** | إعداد قنوات الرسائل: Telegram token، WhatsApp QR، **Mobile devices** (QR إقران + قائمة الأجهزة + إلغاء) — لا مخاطرة هنا |
| Capabilities | يبقى | صورة/صوت/ويب/Dream + **مفاتيح مهارات التداول** (فريق، intel، backtest) |
| System | يبقى | المنطقة الزمنية، خدمة API، إعادة التشغيل، التشخيص |
| Advanced | يبقى | إعادة المحاولة، حدود الأدوات، sandbox، SSRF، gateway |
| About | يبقى | الإصدار، الروابط |
| **Risk Parameters** | **جديد** | نفس مكوّن المنزلقات المستخدم في Connect + أكورديون «متقدم» يحوي بقية الحقول مجمّعة + زر «إعادة إلى ملف المخاطرة» |

تُحذف من التنقل نهائياً: `apps`, `skills`, `automations`, `memory`, `image`, `voice`, `browser` كتبويبات مستقلة (تُدمج داخل Capabilities/System أو تُحذف)، و`system/ChannelsSettings.tsx` اليتيم.

---

## 5. تبسيط الربط وملف المخاطرة: من 73 رقماً + 9 مفاتيح إلى 3 ملفات + 7 منزلقات + 5 مفاتيح

### 5.1 ملفات المخاطرة (Presets) — الاختيار الأول للمستخدم

| الملف | risk/trade | daily loss | max trades | min R:R | news caution | cooldown | spread tol. |
|---|---|---|---|---|---|---|---|
| محافظ Conservative | 0.5% | 2% | 1 | 2.5 | 30 min | 4 h | 45 pts |
| متوازن Balanced (افتراضي) | 1.0% | 3% | 2 | 2.0 | 15 min | 3 h | 60 pts |
| هجومي Aggressive | 2.0% | 5% | 3 | 1.5 | 10 min | 2 h | 80 pts |

اختيار ملف يضبط المنزلقات؛ تحريك أي منزلق يحوّل الملف إلى «مخصص».

### 5.2 المنزلقات السبعة وما تشتقّه

| المنزلق (واجهة) | الحقل الأساسي | المدى/الخطوة | حقول مشتقة آلياً (تختفي من الواجهة) |
|---|---|---|---|
| المخاطرة لكل صفقة % | `risk_pct_default` | 0.25–3 / 0.25 | `risk_pct_max = ×2`، `risk_pct_news_day = ×0.5` |
| حد الخسارة اليومي % | `daily_drawdown_pct` | 1–6 / 0.5 | `equity_spike_pct = ×0.67` |
| أقصى صفقات مفتوحة | `max_open_gold_positions` | 1–4 / 1 (stepper) | `max_total_lots` (T-3.5) = عدد × لوت ملف المخاطرة |
| أدنى عائد/مخاطرة R | `min_rr` | 1.5–3 / 0.25 | `min_rr_live_fill = min_rr − 0.5`، `breakeven_rr = 1.0` ثابت |
| حذر الأخبار (دقائق) | `news_shield_minutes` | 5–45 / 5 | `pre_news_freeze_minutes = ×1.5`، `news_blackout_before_minutes = ×2`، `news_blackout_after_minutes = ×1`، `post_news_entry_wait_minutes = ×1`، `spread_pre_news_minutes = ×0.2` |
| التهدئة بعد الخسائر (ساعات) | `cooldown_after_two_losses_minutes` | 1–6 h / 0.5 | `cooldown_after_two_losses_session_minutes = ÷3`، `cooldown_after_news_stop_minutes = ÷4`، `cooldown_consecutive_losses = 2` ثابت |
| تحمّل السبريد (نقاط) | `spread_max_points` | 30–120 / 5 | `spread_multiplier_pre_news = 3`، `flat_near_entry_points = ×0.5` |

### 5.3 المفاتيح الخمسة (كبيرة، بأيقونة ووصف سطر)

| المفتاح | يجمع |
|---|---|
| درع الأخبار | `news_shield` + `early_exit` (الخروج المبكر يُعرض كخيار فرعي داخل نفس الكارت) |
| قاطع الخسارة اليومي | `drawdown_breaker` |
| قفل التهدئة | `cooldown_lock` |
| حارس السبريد | `spread_guard` |
| أقفال الجلسة والعطل | `session_lock` + `holiday_lock` |

`rr_filter` و`max_positions` يصبحان **دائمَي التفعيل** (قيمتهما تُضبط بالمنزلقات)؛ يبقيان قابلَي التعطيل من Settings → Risk Parameters → متقدم فقط.

### 5.4 لوحة التحكم (Connect) — ثلاثة عناصر فقط

| العنصر | النوع | الخلفية |
|---|---|---|
| Kill Switch | زر أحمر بتأكيد مزدوج (اسحب للتأكيد) | `runtime_state.kill_switch` + `mt5_close_position(flatten_all)` |
| وضع التشغيل | segmented: **توصيات فقط** / **اقتراح + تأكيد** / **إدارة آلية للمفتوح** | `paper_mode`، تفعيل `management/engine` (T-8.1) |
| إيقاف مؤقت | مفتاح | `runtime_state.paused` |

### 5.5 بطاقات الاتصال (Connect) — كل بطاقة: حالة + زر واحد

| البطاقة | الحالة المعروضة | الزر |
|---|---|---|
| تدفق الأسعار (OANDA) | متصل/منقطع + آخر تيك + سبريد | «إعداد» (token/account/env) |
| الوسيط (MT5 عبر MetaAPI) | متصل/غير مهيأ + الرصيد + الهامش | «ربط» (token/account/region — تُخزَّن مشفّرة T-7.2) |
| Telegram | مفعّل/معطّل + اسم البوت | «فتح الإعدادات → Channels» |
| WhatsApp | مقترن/غير مقترن | QR |
| الجوال | عدد الأجهزة | QR إقران (05) |

### 5.6 مصير بقية الحقول (≈50 حقلاً)

| المجموعة | الحقول | القرار |
|---|---|---|
| ثوابت المحرك (لا يفهمها المستخدم) | `midnight_spread_*` (4), `rollover_*` (3), `daily_close_*` (2), `news_void_seconds`, `first_minute_dead`, `ping_max_ms`, `exec_latency_max_ms`, `slippage_probe_points`, `lot_dual_check_*` (2), `news_candle_volume_z`, `g7_max_slippage_atr`, `liquidity_proximity_atr`, `entry_max_atr_distance`, `target_max_atr_distance`, `half_distance_pct`, `max_reprice_rounds`, `stale_quote_seconds`, `disconnect_alert_seconds`, `margin_min_pct` | **تُحذف من الواجهة**؛ تبقى في `TradingRiskParameters` قابلة للتحرير من `config.json` فقط |
| إدارة الصفقة | `partial_tp1_pct`, `partial_tp2_pct`, `partial_tp_split_*` (3), `profit_lock_*` (2), `trail_atr_mult`, `overnight_sl_buffer_points`, `post_news_sl_buffer_points`, `time_stop_hours` | Settings → Risk Parameters → **متقدم / إدارة الصفقة** (منزلقات أيضاً) |
| التنفيذ | `proposal_ttl_seconds`, `max_confirm_slippage_points`, `slippage_max_points` | متقدم / التنفيذ |
| التقلب | `adr_chase_multiple`, `gap_no_chase_points`, `news_candle_atr_mult`, `news_candle_m1_points`, `news_candle_m5_adr_pct`, `atr_double_lot_halve`, `emergency_move_points_per_minute`, `bad_tick_points` | متقدم / التقلب |
| المعلّق | `idea_stale_hours`, `pending_ttl_hours` | متقدم / الأوامر المعلقة |

### 5.7 تغييرات الخلفية المطلوبة للتبسيط

| الملف | التغيير |
|---|---|
| `nanobot/config/schema.py` | إضافة `risk_profile: Literal["conservative","balanced","aggressive","custom"]` + `max_total_lots` إلى `TradingRiskParameters` |
| `nanobot/trading/risk_profiles.py` (جديد) | جداول الملفات + دالة `derive_parameters(primary: RiskPrimaryInputs) -> TradingRiskParameters` (المشتقات في 5.2) + اختبار خصائص (كل المشتقات داخل الحدود) |
| `nanobot/webui/trading_risk_api.py` | مسار `POST /api/settings/trading-risk/profile` + `RISK_FIELD_SPECS` تحصل على `tier: primary|advanced|hidden` |
| `nanobot/trading/risk_state.py` | لا تغيير في `OPERATOR_TOGGLES`؛ الواجهة تجمعها فقط |

---

## 6. لغة الواجهة والنصوص

- كل نص في `webui/src/app/i18n/{ar,en}.json`؛ نقل `lib/trading/cardLocale.ts`, `gate-labels.ts`, `stage-labels.ts` إليهما وحذفها.
- الواجهة العربية أولاً (RTL) مع إنجليزية كاملة؛ تسميات البوابات/المراحل تأتي من الخادم (`nanobot/trading/locales/*.json` — انظر 01/D8) عبر `/api/trading/labels?locale=` حتى لا تتكرر في مكانَين.
- لا أرقام مكتوبة بالخط العربي الهندي؛ الأرقام لاتينية دائماً (`Intl.NumberFormat("en-US")`).

## 7. الترحيل والقطع (cut-over)

1. بناء `webui/src/app/` خلف `?ui=v2` وحفظ الاختيار في `localStorage`.
2. ترحيل المكونات حسب القائمة (القسم 1/B) مع تنقية النصوص.
3. اختبارات Vitest للأقسام الخمسة + الإعدادات + المنزلقات (المشتقات).
4. لقطات شاشة مقارنة (desktop/mobile/RTL) في PR.
5. القطع: `main.tsx` → `app/main.tsx`؛ حذف `App.tsx`, `Sidebar.tsx`, `components/settings/*`, `components/trading/*` غير المرحّل، `pages/ChartHostPage.tsx` يُنقل إلى `app/chart-host/`.
6. `cd webui && bun run build && bun run test && bun run lint` أخضر؛ `nanobot/web/dist` لا يحوي ملفات الواجهة القديمة.
