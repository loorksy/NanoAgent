# 08 — صلاحيات الوكيل على حساب MT5

> جزء من خطة NanoAgent v2 — انظر [`00-master-plan.md`](./00-master-plan.md)
> قرار المالك (الرسالة 2): «توصيات واقتراحات وتنفيذ، حسب الصلاحيات المعطاة للوكيل عندما يكون متصلاً بحساب MT5».

---

## 1. الوضع الحالي

| ما هو موجود | المسار |
|---|---|
| تنفيذ عبر MetaAPI بنمط اقتراح → تأكيد يدوي (`operator_must_confirm: True` دائماً) | `nanobot/trading/mt5_execution.py` (`mt5_propose_order` 194، `mt5_confirm_order` 257) |
| بوابة `hitl` مقفلة ضمن `LOCKED_INTEGRITY_TOGGLES` — لا يستطيع المشغّل تعطيلها | `nanobot/trading/risk_state.py` 44–52، `gates/execution.py` 132 |
| `paper_mode=True` افتراضياً، `kill_switch`, `paused` | `nanobot/trading/runtime_state.py` |
| حدود رقمية (risk %, max positions, drawdown…) | `TradingRiskParameters` (`config/schema.py` 369) |
| بيانات MetaAPI (`token`, `account_id`, `region`) بدون تشفير | `TradingMetaApiConfig` (`config/schema.py` 352) |
| **لا يوجد** مفهوم «صلاحية» منفصل: إمّا يستطيع الوكيل اقتراح كل شيء أو لا شيء | — |

النتيجة: اليوم مستوى واحد فقط (اقتراح + تأكيد). المطلوب ثلاثة مستويات ومنح مُقيَّدة.

---

## 2. المستويات

| المستوى | الاسم في الكود | ما يفعله الوكيل | ما يراه المستخدم |
|---|---|---|---|
| 0 | `recommend` | يصدر توصيات وسيناريوهات فقط؛ أدوات `mt5_propose_order/modify/close` **غير مسجّلة** في الدور (D5 يسجّلها لكن بعقد يرجع خطأ `permission.level_recommend_only`) | كروت `decision` بلا زر تنفيذ |
| 1 | `propose` (**الافتراضي** عند ربط حساب) | كما اليوم: يقترح، وكل تنفيذ يحتاج تأكيداً بشرياً ضمن TTL | كرت `approval` بأزرار تأكيد/إلغاء (ويب، جوال، إشعار) |
| 2 | `execute` | ينفّذ بلا تأكيد **فقط** داخل المنح المقيَّدة (§3)؛ ما يتجاوزها يهبط تلقائياً إلى `propose` | كرت `decision` + سطر «نُفِّذ ضمن الصلاحية X»؛ إشعار فوري بعد التنفيذ |

قواعد لا تُناقش:

- `paper_mode=True` يجعل أي مستوى ≥1 ينفّذ على الورق فقط؛ الخروج من الورق قرار صريح في الواجهة مع تأكيد مزدوج.
- `kill_switch` و`paused` يعلوان على أي مستوى.
- البوابات G1–G20 تُقيَّم في كل المستويات؛ المستوى 2 لا يُسقِط أي بوابة سوى `hitl` (تُستبدل بـ `permission` §4).
- المستوى 2 غير متاح في اليوم الأول للربط (`grace_hours` افتراضي 24) — الوكيل يهبط إلى `propose` ويقول ذلك.

---

## 3. المنح المقيَّدة (Scopes)

تُطبَّق على المستوى 2 فقط؛ المستوى 1 يعرضها كتحذير في كرت الاقتراح (مثلاً «يتجاوز اللوت المسموح» فيُرفض عند التأكيد).

| المنحة | الحقل | افتراضي | معناها |
|---|---|---|---|
| فتح صفقات | `can_open: bool` | `false` | إرسال أوامر سوق/معلّقة |
| تعديل SL/TP | `can_modify_sl_tp: bool` | `true` | تحريك الوقف/الهدف (اتجاه الحماية فقط ما لم يُفعَّل `allow_widen_stop`) |
| توسيع الوقف | `allow_widen_stop: bool` | `false` | يبقى ممنوعاً افتراضياً (`gate.stop_widen` موجودة) |
| إغلاق جزئي | `can_partial_close: bool` | `true` | TP1 وخفض المخاطر |
| إغلاق كلي | `can_close_all: bool` | `false` | إغلاق كل صفقات الذهب دون تأكيد |
| أوامر معلّقة | `can_place_pending: bool` | `false` | يتطلب T-4.1 |
| أقصى لوت لكل أمر | `max_lot_per_order: float` | يُشتق من ملف المخاطرة (04 §4.1) | يُخفَّض تلقائياً إلى القيمة المسموحة ما لم يكن `hard=true` فيُرفض |
| أقصى إجمالي لوت | `max_total_lots: float` | من `TradingRiskParameters.max_total_lots` (T-3.5) | يشمل الصفقات المفتوحة |
| سقف خسارة يومي للتنفيذ التلقائي | `auto_daily_loss_pct: float` | 50% من `daily_drawdown_pct` | بعده يهبط المستوى إلى `propose` لبقية اليوم |
| نوافذ الجلسة | `sessions: list[london, newyork, asia, overlap]` | `[london, newyork]` | خارجها → `propose` |
| منع حول الأخبار | `news_lock: bool` | `true` (مقفل) | يعتمد على `news_window` الحالية |
| صلاحية زمنية | `expires_at: int | null` | 7 أيام | بعد الانتهاء يعود المستوى إلى `propose` ويُخطر المستخدم |
| تأكيد بيومتري للترقية | `upgrade_requires_biometric: bool` | `true` (جوال) | رفع المستوى من التطبيق يطلب بصمة |

نموذج البيانات (`nanobot/trading/permissions/model.py`):

```python
class Mt5Permissions(Base):
    level: Literal["recommend", "propose", "execute"] = "propose"
    can_open: bool = False
    can_modify_sl_tp: bool = True
    allow_widen_stop: bool = False
    can_partial_close: bool = True
    can_close_all: bool = False
    can_place_pending: bool = False
    max_lot_per_order: float | None = None      # None → مشتق من ملف المخاطرة
    max_total_lots: float | None = None
    auto_daily_loss_pct: float | None = None
    sessions: list[str] = ["london", "newyork"]
    news_lock: bool = True
    expires_at: int | None = None
    grace_hours: int = 24
    granted_at: int = 0
    granted_by: str = ""                         # client id من البوابة (07 §8)
```

---

## 4. نقاط التنفيذ (Enforcement)

نقطة واحدة قابلة للاختبار لكل عملية، **قبل** البوابات وليس بدلاً منها:

```
nanobot/trading/permissions/
├── model.py       # Mt5Permissions (Pydantic) + الاشتقاق من risk_profile
├── store.py       # حفظ مشفّر (secret_store, T-7.2) + سجل تغييرات
├── evaluate.py    # evaluate_permission(action, ctx) -> PermissionDecision
└── __init__.py
```

| العملية | `action` | القرار الممكن |
|---|---|---|
| `mt5_propose_order` | `open` | `deny` (recommend) · `propose` · `execute` |
| `mt5_modify_order` | `modify_sl_tp` / `widen_stop` | `deny` · `propose` · `execute` |
| `mt5_close_position(partial)` | `partial_close` | … |
| `mt5_close_position(all)` | `close_all` | … |
| أوامر معلّقة (T-4.1) | `place_pending` | … |

`PermissionDecision = {mode: deny|propose|execute, reason_key, adjusted_lot?, downgrade_reason_key?}`.

التكامل:

1. في `gates/execution.py::collect_execution_checks` تُضاف بوابة `permission` بعد `hitl`: تمرّر إذا `operator_confirmed=True` **أو** `PermissionDecision.mode == "execute"`. بوابة `hitl` تبقى مقفلة كما هي؛ فقط تُعامل «تنفيذاً ضمن صلاحية» على أنه تأكيد صادر من المشغّل مسبقاً (`operator_confirmed_by="permission:<granted_by>"`) ويُسجَّل كذلك.
2. `mt5_propose_order` يستدعي `evaluate_permission("open")`: `deny` → خطأ أداة تعليمي؛ `propose` → كما اليوم؛ `execute` → ينشئ الاقتراح ويستدعي `mt5_confirm_order(confirm=True, confirmed_by=...)` فوراً في نفس الدور، ويبث `approval` بحالة `auto_confirmed` للـ Timeline.
3. `max_lot_per_order`: إذا `sized > max` → `adjusted_lot = max` (ويُذكر في الكرت)، إلا إذا `hard=true` فيُرفض.
4. أي هبوط تلقائي (`auto_daily_loss_pct`, خارج الجلسة، انتهاء الصلاحية، grace) يبث `notification` عبر البوابة (07 §7) ويُكتب في `/log`.
5. عقد الأدوات في البرومبت (02 §3 `40_tool_contracts.md`) يشرح المستويات كي يعرف الوكيل متى يقول «أوصي» ومتى «أقترح» ومتى «نفّذت» — بدون كلمات مفتاحية؛ المستوى الحالي يُحقن في `70_dynamic/`.

---

## 5. التخزين والأمان

- `store.py` يحفظ `Mt5Permissions` في `security/secret_store.py` (Fernet، T-7.2) بجانب `TradingMetaApiConfig.token`؛ أي تغيير مستوى/منحة يُسجَّل بـ (`who`, `from`, `to`, `ts`) في `permissions_audit`.
- رفع المستوى إلى `execute` يتطلب: `paper_mode` صريح أو تأكيد مزدوج للحساب الحقيقي، نطاق `control` في التوكن (07 §8)، وبيومترياً من الجوال.
- خفض المستوى أو Kill Switch لا يتطلب شيئاً (زر واحد).
- الوكيل **لا** يستطيع تعديل صلاحياته: لا أداة `set_permissions`؛ المسار الوحيد `PUT /api/v2/connect/mt5/permissions` من عميل بشري.
- لا نص عربي في `evaluate.py`؛ كل الأسباب `reason_key` تُترجم من `locales/*.json`.

---

## 6. الواجهة

**الربط (`/connect`)** — بطاقة «صلاحيات MT5» تحت بطاقة اتصال MetaAPI (04 §4.5):

- محدد ثلاثي: توصيات فقط · اقتراح + تأكيد · تنفيذ ضمن الحدود.
- عند «تنفيذ»: 4 مفاتيح (فتح، إغلاق كلي، أوامر معلّقة، توسيع الوقف) + منزلق واحد (أقصى لوت لكل أمر) + اختيار الجلسات + مدة الصلاحية (1 يوم / 7 أيام / 30 يوماً).
- شارة الحالة الحالية دائماً: «المستوى الفعلي الآن: اقتراح (خارج الجلسة)» عند الهبوط التلقائي.
- الباقي (`auto_daily_loss_pct`, `grace_hours`, `max_total_lots`) في «متقدم».

**الوكيل (`/agent`)** — كرت `decision` يعرض المستوى المطبَّق؛ كرت `approval` عند `propose`.

**السجل (`/log`)** — كل تغيير صلاحية، كل تنفيذ تلقائي مع المنحة التي سمحت به، كل هبوط تلقائي وسببه.

**الجوال (05)** — نفس البطاقة مختصرة؛ الترقية تطلب بصمة.

---

## 7. الترتيب والاعتماديات

| الخطوة | المحتوى | يعتمد على |
|---|---|---|
| P1 | `permissions/model.py` + `store.py` + اختبارات الاشتقاق من ملف المخاطرة | T-7.2 secret store، 04 §4.7 `risk_profiles.py` |
| P2 | `evaluate.py` + بوابة `permission` في `gates/execution.py` + اختبارات (propose/execute/deny، هبوط تلقائي، TTL) | P1 |
| P3 | ربط `mt5_propose_order/modify/close` + بث `approval(auto_confirmed)` | P2، 07/G4 |
| P4 | REST `GET/PUT /connect/mt5/permissions` + audit في `/log` | 07/G7 |
| P5 | بطاقة الواجهة في Open WebUI fork + الجوال | 04، 05 |
| P6 | أوامر معلّقة (`can_place_pending`) | T-4.1 |

---

## 8. معايير القبول

- المستوى `recommend`: الوكيل يجيب بتوصية ولا يظهر أي كرت `approval`؛ استدعاء أداة تنفيذ يعيد خطأ تعليمياً ولا يلمس MetaAPI (mock transport).
- المستوى `propose`: سلوك اليوم بالضبط (اختبارات `tests/trading/test_mt5_*` الحالية تبقى خضراء).
- المستوى `execute` مع `can_open=true`, `max_lot_per_order=0.1`: اقتراح بلوت 0.3 يُنفَّذ بلوت 0.1 مع ذكر التعديل؛ مع `hard=true` يُرفض.
- `execute` خارج الجلسات المسموحة أو بعد `auto_daily_loss_pct` أو بعد `expires_at` → يهبط إلى `propose` ويبث `notification` ويُسجَّل.
- `kill_switch=true` أو `paused=true` يمنع التنفيذ في كل المستويات.
- لا يمكن رفع المستوى بتوكن بلا نطاق `control`؛ لا يوجد أي أداة للوكيل تغيّر الصلاحيات (اختبار على `ToolRegistry`).
- `rg "[\u0600-\u06FF]" nanobot/trading/permissions/` → صفر.
