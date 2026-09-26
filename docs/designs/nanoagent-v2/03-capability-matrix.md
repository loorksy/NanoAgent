# 03 — مصفوفة القدرات مقابل وثيقة XAUUSD Core Engine

> جزء من خطة NanoAgent v2 — انظر [`00-master-plan.md`](./00-master-plan.md)
> الحالة من الكود الفعلي (`nanobot/trading/`, `tests/trading/`) لا من الوثائق.
> **DONE** = مُنفَّذ ومختبَر · **PARTIAL** = موجود لكنه ناقص/غير مربوط · **MISSING** = غير موجود

**الإجمالي: 27 DONE · 21 PARTIAL · 2 MISSING** (من 50 قدرة + النقاش متعدد الوكلاء).

سياسة التنفيذ الحالية في الكود: التحليل «توصيات فقط»؛ التنفيذ عبر MetaAPI موجود بنمط **propose → confirm** (HITL إلزامي، `paper_mode=True` افتراضياً)؛ OANDA لبيانات السوق فقط.

---

## 1. التحليل الفني

| # | القدرة | الحالة | الدليل | الفجوة → المهمة |
|---|---|---|---|---|
| 1.1 | Supply/Demand + FVG (3 شموع، ممتلئة/جزئية) | DONE | `geometry/detectors.py` `build_supply_demand_zones`, `detect_fair_value_gaps`, `_gap_fill`; `agents/supply_demand.py` | — |
| 1.2 | توافق الاتجاه M15/H1/H4/D1 | PARTIAL | `agents/multi_timeframe.py` — «daily» مُشتقّ من H1 | **T-1.2** تحميل D1 حقيقي من OANDA + مصفوفة توافق صريحة (4 أطر) في `MultiTimeframeResult` + اختبار |
| 1.3 | الكسر الكاذب / Sweeps / Turtle Soup | DONE | `detectors.detect_sweeps`, `find_equal_levels`; `agents/liquidity.py`; قالب DTW `turtle_soup` | — |
| 1.4 | بنية السوق BOS/CHoCH | DONE | `detectors.find_swings`, `detect_structure_events` | — |
| 1.5 | فيبوناتشي آلي + S/R ديناميكي | DONE | `detectors.fibonacci_retracement`, `support_resistance`; `geometry/snapshot.py` | — |
| 1.6 | Tick Volume + ATR | PARTIAL | `compute_atr`; volume-z في `gates/news_candle.py` فقط | **T-1.6** مؤشر زخم بالـ tick volume للدخول (`momentum_score`) داخل `GeometryNode` + استهلاكه في عقد القرار |
| 1.7 | Divergence RSI/MACD | DONE | `compute_rsi`, `compute_macd`, `detect_divergence` | — |

## 2. الماكرو

| # | القدرة | الحالة | الدليل | الفجوة → المهمة |
|---|---|---|---|---|
| 2.1 | التقويم الاقتصادي + الفارق فعلي/متوقع | DONE | `intel/calendar_scraper.py` `_surprise`; `news/forex_factory.py` | — |
| 2.2 | DXY وارتباطه بالذهب | DONE | `intel/intermarket.py` `intermarket_snapshot`, `divergence_matrix` | يحتاج مصدر (yfinance/MT5) وإلا `source=unavailable` |
| 2.3 | نبرة الفيدرالي Hawkish/Dovish | DONE | `intel/local_sentiment.py`, `intel/vip_tracker.py` | القوائم اللفظية تُنقل إلى `lexicon/*.json` (02) |
| 2.4 | رادار جيوسياسي | DONE | `intel/regex_emergency.py`, `rss_aggregator.py`, `telegram_scraper.py` | — |

## 3. إدارة المخاطر

| # | القدرة | الحالة | الدليل | الفجوة → المهمة |
|---|---|---|---|---|
| 3.1 | حجم اللوت من % المخاطرة + مسافة الوقف | DONE | `gates/position_sizing.py` `lot_from_balance` | — |
| 3.2 | Daily Drawdown Breaker | DONE | `gates/drawdown_breaker.py` | التسطيح flatten يبقى HITL (مقصود) |
| 3.3 | Spread Guard | DONE | `gates/spread_guard.py` | — |
| 3.4 | Cooldown Lock | DONE | `gates/cooldown_lock.py`; `risk_state.record_loss` | — |
| 3.5 | سقف الصفقات/العقود المتزامنة | PARTIAL | `gates/max_positions.py` — عدد فقط | **T-3.5** إضافة `max_total_lots` إلى `TradingRiskParameters` + الفحص في `collect_execution_checks` |
| 3.6 | R:R ≥ 1:2 | DONE | `gates/rr_filter.py` | — |

## 4. التنفيذ وإدارة الصفقة — **القسم الأضعف (0 DONE / 6 PARTIAL)**

| # | القدرة | الحالة | الدليل | الفجوة → المهمة |
|---|---|---|---|---|
| 4.1 | تنفيذ MT5 (Market + Pending) | PARTIAL | `mt5_execution.py`, `mt5_metaapi.SdkTransport.send_market` — الأوامر المعلقة تُقبل عند الاقتراح لكن التأكيد يرسل market دائماً | **T-4.1** `send_pending(limit/stop)` في `SdkTransport` + مسار تأكيد + إلغاء معلق + اختبار |
| 4.2 | Trailing Stop (swing أو ATR) | PARTIAL | `gates/trade_management.trailing_stop` (ATR فقط، غير آلي) | **T-4.2** محرك إدارة صفقات دائم `trading/management/engine.py` (async) يقترح/ينفّذ trailing swing+ATR بحسب وضع التأكيد |
| 4.3 | Auto Breakeven بعد TP1 | PARTIAL | `should_move_to_breakeven` عند 1R | **T-4.3** شرط «بعد TP1» + تنفيذ عبر `mt5_modify_order` من المحرك |
| 4.4 | Partial TP | PARTIAL | نسب محسوبة؛ `close_position` كامل فقط | **T-4.4** `close_partial(ticket, volume)` في transport + استخدامه من المحرك |
| 4.5 | News Shield | PARTIAL | يمنع الدخول ويلغي المعلق؛ لا يؤمّن المفتوح | **T-4.5** إجراء «secure open trades» (BE/تضييق/تنبيه) قبل الخبر بـ `news_shield_minutes` من المحرك |
| 4.6 | خروج مبكر عند ضعف الزخم | PARTIAL | toggle `early_exit` فقط | **T-4.6** كاشف ضعف زخم (شمعتان عكسيتان M5 + momentum_score من T-1.6) → توصية/اقتراح خروج |

## 5. الذاكرة والتعلم

| # | القدرة | الحالة | الدليل | الفجوة → المهمة |
|---|---|---|---|---|
| 5.1 | بحث نماذج مماثلة تاريخياً | DONE | `intel/vector_playbook.py`; أداة `trading_intel` | — |
| 5.2 | Fast Backtest (100–200 شمعة) | **MISSING** | مُستثنى صراحة في `skills/memory-review` | **T-5.2** ترحيل `foxagent/backend/app/services/backtest/` (محرك replay) كـ `trading/backtest/` + أداة `fast_backtest` (انظر 06) |
| 5.3 | تحليل ذاتي بعد كل صفقة | DONE | `intel/postmortem.py` `record_stop_hit` | — |
| 5.4 | سجل الدروس كفحوص مسبقة | DONE | `postmortem.refuse_repeat_error` من `kernel.py` | — |
| 5.5 | مراجعة ثنائية (فني + مخاطر) | DONE | `StructureNode`+`RiskNode` + `gates/execution.py` | — |

## 6. التنبيهات والتواصل

| # | القدرة | الحالة | الدليل | الفجوة → المهمة |
|---|---|---|---|---|
| 6.1 | تنبيه فوري + صورة شارت مرسومة | DONE | `stage_delivery.py`, `chart_photo.py`, `drawings/plan.py`, `capture_service.py` | — |
| 6.2 | أزرار موافقة/إلغاء قبل التنفيذ | PARTIAL | `mt5_confirm_order(confirm=...)` أداة؛ الموافقة الورقية في الكارت | **T-6.2** زر «تأكيد التنفيذ» على كارت التوصية (Web/Mobile) + أزرار inline في Telegram تستدعي `POST /api/trading/proposals/{id}/confirm|cancel` |
| 6.3 | تقرير صباحي قبل لندن/نيويورك | PARTIAL | مهارة فقط | **T-6.3** مهمة نظام اختيارية `morning_briefing` (07:30 London / 13:00 NY بتوقيت المشغّل) تولّد artifact + إرسال متعدد القنوات |
| 6.4 | تقارير أداء دورية | PARTIAL | `daily_pnl_pct`; `memory/decisions.py` | **T-6.4** `trading/reports/scorecard.py` (PnL, win rate, avg R, max DD) + مهمة يومية/أسبوعية + صفحة Log |
| 6.5 | رد لحظي باللغة الطبيعية | DONE | أدوات + حلقة الوكيل | يبقى بعد حذف الراوتر (01) |
| 6.6 | تنبيه انقطاع الأسعار | PARTIAL | `gates/stale_quote.py` يحجب فقط | **T-6.6** heartbeat monitor في `oanda_stream.py` → حدث `feed_disconnected` → fan-out |
| 6.7 | بث متزامن Telegram + المنصة | PARTIAL | `TradingStagePublisher` للقناة الحالية فقط | **T-6.7** `trading/delivery.py::broadcast(event, channels=all_enabled)` + Mobile push (05) |

## 7. الأمان والاستقرار

| # | القدرة | الحالة | الدليل | الفجوة → المهمة |
|---|---|---|---|---|
| 7.1 | Master Kill Switch | DONE | `runtime_state.kill_switch`; `mt5_close_position(flatten_all=True)` | زر واحد في Connect + Mobile (04/05) |
| 7.2 | تشفير مفاتيح الحساب محلياً | **MISSING** | التوكن في config/env بنص صريح | **T-7.2** ترحيل نمط `foxagent settings_store` (Fernet) → `nanobot/security/secret_store.py`؛ مفتاح من keyring أو `NANOAGENT_SECRET_KEY` |
| 7.3 | حفظ حالة الصفقات SQLite | DONE | `intel/tickets.py` `TicketStore`; `recommendations/store.py` | — |
| 7.4 | Bad Tick Filter | DONE | `gates/bad_tick.py` | — |
| 7.5 | تبني الصفقات اليدوية | DONE | `TicketStore.adopt`, `mt5_get_account(adopt_ticket=)` | إشعار استباقي عند اكتشاف صفقة يدوية (T-8.1) |

## 8. المهام المتعددة

| # | القدرة | الحالة | الدليل | الفجوة → المهمة |
|---|---|---|---|---|
| 8.1 | مسح مستمر أثناء إدارة صفقة (async) | PARTIAL | cron اختياري (معطّل افتراضياً)؛ `bots/coordinator.py` | **T-8.1** خدمة `trading/management/engine.py` دائمة (asyncio task داخل gateway) تدير المفتوح + تمسح + تكتشف اليدوي؛ تُفعَّل من Connect |
| 8.2 | سيناريوهان مشروطان وتفعيل الأسبق | PARTIAL | `alternativeScenario` سردي فقط | **T-8.2** `trading/scenarios/trigger_engine.py`: يسجّل سيناريوهين بشروط سعرية، يراقب التيكات، يفعّل واحداً ويلغي الآخر، ثم يقترح HITL |
| 8.3 | فصل سكالبينج/سوينج (Magic Numbers) | DONE | `policy.MAGIC_SCALP/MAGIC_SWING`; `mt5_propose_order(style=)` | — |
| 8.4 | أوامر بلغة طبيعية على الصفقات النشطة | PARTIAL | الأدوات موجودة؛ لا اختبار للنية | يتحقق تلقائياً مع الوكيل الواحد (01) + عقد الأدوات (02) + اختبار سيناريو «انقل كل الوقفات للدخول» |
| 8.5 | مفاتيح تفعيل من لوحة | DONE | `risk_state.OPERATOR_TOGGLES`; `RiskParametersSettings.tsx` | تُعاد صياغتها كمفاتيح كبيرة في Connect (04) |

## 9. الشخصية والسلوك

| # | القدرة | الحالة | الدليل | الفجوة → المهمة |
|---|---|---|---|---|
| 9.1 | أنماط تواصل متكيفة | PARTIAL | برومبت فقط | طبقة `60_behaviour.md` + `tone_profile` في الإعدادات (02) |
| 9.2 | اعتراف بالخطأ بعد الوقف | PARTIAL | `record_stop_hit` بدون رسالة | **T-9.2** عند انتقال الخطة إلى `invalidated` يولّد المحرك artifact «post-mortem» ويرسله (fan-out) |
| 9.3 | صمت في السوق العرضي | PARTIAL | مهارة؛ البوت قد يرسل «compressed range» | **T-9.3** بوابة صمت حتمية في `delivery.broadcast`: لا إشعار استباقي إذا `regime=range` ولا تغيّر مادي |
| 9.4 | سؤال تأملي نهاية اليوم | PARTIAL | سطر في SOUL | **T-9.4** مهمة `daily_wrap` اختيارية + تخزين الإجابة في `memory/journal.jsonl` |

## + النقاش متعدد الوكلاء

| القدرة | الحالة | الدليل | المهمة |
|---|---|---|---|
| Debate / Committee / War-room / MTF panel | DONE | `crew/debate.py`, `teams/runtime.py`, `presets/*.yaml`, أداة `run_trading_team` | ربط `system_prompt` الفعلي (02) + عرض حي في Agent view (04) |

---

## ملخص المهام الناتجة (تُرحَّل إلى المراحل في 00)

| المهمة | القسم | الحجم | يعتمد على |
|---|---|---|---|
| T-1.2 D1 حقيقي + مصفوفة توافق | 1 | S | — |
| T-1.6 momentum_score | 1 | S | — |
| T-3.5 max_total_lots | 3 | XS | — |
| T-4.1 pending orders transport | 4 | M | — |
| T-4.2/4.3/4.4/4.5 محرك إدارة الصفقات | 4 | **L** | T-4.1, T-8.1 |
| T-4.6 كاشف ضعف الزخم | 4 | M | T-1.6 |
| T-5.2 fast backtest (من foxagent) | 5 | M | 06 |
| T-6.2 أزرار تأكيد التنفيذ | 6 | M | 04, 05 |
| T-6.3 morning briefing | 6 | S | T-6.7 |
| T-6.4 scorecard + تقارير | 6 | M | — |
| T-6.6 feed heartbeat | 6 | S | T-6.7 |
| T-6.7 broadcast متعدد القنوات | 6 | M | 05 (mobile channel) |
| T-7.2 secret store مشفّر (من foxagent) | 7 | S | 06 |
| T-8.1 خدمة الإدارة الدائمة | 8 | **L** | — |
| T-8.2 trigger engine للسيناريوهين | 8 | M | T-8.1 |
| T-9.2/9.3/9.4 سلوك تشغيلي | 9 | S | T-6.7 |

الأحجام: XS < 100 سطر · S ≈ ملف واحد + اختبار · M ≈ 2–4 ملفات + اختبارات · L ≈ حزمة فرعية جديدة.
