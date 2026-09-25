# 01 — تدقيق مسار الوكيل: وكيل حقيقي واحد أم ترقيع؟

> جزء من خطة NanoAgent v2 — انظر [`00-master-plan.md`](./00-master-plan.md)
> المصدر: قراءة الكود الفعلي في `nanobot/agent/` و `nanobot/trading/` (لا اعتماد على وثائق التصميم).

---

## 1. الحكم المختصر

**الوضع الحالي: هجين يميل إلى الترقيع (patched hybrid).**

- المسار الافتراضي (`LONORA_AGENT_FIRST=true`, `LONORA_UNIFIED_LOOP` غير مضبوط) يشغّل `AgentLoop` حقيقياً واحداً يختار فيه النموذج الأدوات بنفسه — هذا الجزء سليم.
- لكن التداول **مركّب فوق الحلقة** لا مدمج فيها: راوتر كلمات مفتاحية (عربي + إنجليزي) داخل الكود، مسار سريع يتجاوز النموذج، مخطط أدوار (`turn_planner`) يقرر «نمط الدور» بالكود، شخصيتان (`nanobot` في `SOUL.md` و`Lonora` في المهارات والـ synthesizer)، وأنبوبتان متوازيتان (`orchestrator.py` و`kernel.py`) يتحكم بهما ثلاث متغيرات بيئة (`LONORA_AGENT_FIRST`, `LONORA_UNIFIED_LOOP`, `LONORA_PLANNER_SHADOW`).
- قرار BUY/SELL لا يصدره وكيل المحادثة، بل **نموذج LLM ثانٍ** (`run_final_decision_synthesizer`) ببرومبت مستقل (`synth_prompt.py`) ثم بوابات حتمية G1–G20. هذا بحد ذاته تصميم سلامة مقبول (لا أسعار مُختلقة، البوابات لا تقلب الاتجاه)، لكنه اليوم **شخصية ثانية** لا «أداة» يملكها الوكيل الواحد.

**الخلاصة:** ليس وكيلاً واحداً بمسار واحد مثل Claude Code / Cursor. يمكن تحويله إلى ذلك بحذف طبقة التوجيه بالكلمات وتوحيد المسار والشخصية، دون التخلي عن نواة السلامة (synthesizer كأداة + gates).

---

## 2. الأدلة — أين يُحقن التداول داخل الحلقة العامة

### 2.1 `nanobot/agent/loop.py` (2484 سطراً)

| الأسطر | ما يحدث | التصنيف |
|---|---|---|
| 459–461 | تسجيل `gold_intent_runtime_context` كمزوّد سياق تشغيلي | مقبول (سياق فقط، لا توجيه) |
| 1689–1717 | قراءة `LONORA_UNIFIED_LOOP`، ربط `TurnSession` + `validate_turn_input`، تخطّي `gold_fast_path` إذا `on`، ثم تمرير كل خرج عبر `finalize_turn_outbound` | ترقيع: ثلاث سلوكيات مختلفة بحسب env var |
| 1722–1733 | `_finalize_unified_outbound` → سياسة خرج / shadow logging | ترقيع (يعمل فقط في وضعين من ثلاثة) |
| 1859–1907 | `_dispatch_gold_fast_path` — تجاوز النموذج كلياً بالكلمات المفتاحية عندما `agent_first_mode=False` | **ترقيع صريح** |

`nanobot/agent/runner.py` نظيف من أي فرع تداولي. `nanobot/agent/tools/execution.py` (148–154) يربط interceptor سياسة التداول عند `unified_loop_serving()`.

### 2.2 التوجيه بالكلمات المفتاحية (`nanobot/trading/`)

| الملف | الدور | المشكلة |
|---|---|---|
| `operator_keywords.py` (152 سطراً) | قوائم regex عربية/إنجليزية: سعر، حلل، توصية، شراء/بيع، ذهب، لجنة، مناظرة، صورة، … | **31 سطراً عربياً داخل منطق الكود**؛ التوجيه يعتمد على مطابقة نصية |
| `intent_router.py` → `route_intent()` (45–68) | تسجيل نقاط للـ patterns وإصدار `RoutedIntent` بثقة ثابتة (0.5–0.9) | القرار بالكود لا بالنموذج |
| `turn_planner.py` → `plan_turn()` (74–178) | يحوّل النية + حالة الخطة الحية إلى `mode` (`full_analysis`, `gate_report`, `recommendation_followup`, `team_swarm`, …) | يقرر ما سيفعله الوكيل قبل أن يرى النموذج الرسالة |
| `capabilities/planner.py`, `node_planner.py`, `node_sets.py` | اختيار «بطاقات القدرات» وعُقد الأدلة بحسب كلمات | نفس المشكلة |
| `fast_path.py` (258) + `turn_executor.py` (394) | تنفيذ مباشر بدون LLM لمسارات السعر/الشارت/المتابعة/تقرير البوابات | مسار موازٍ كامل |
| `output_policy.py` | إعادة كتابة كلمتي شراء/بيع بالعربية في الخرج | 4 أسطر عربية في منطق ما بعد الرد |

### 2.3 المسارات المتوازية (ستة مسارات لرسالة واحدة)

1. حلقة الوكيل الافتراضية (LLM + أدوات).
2. `gold_fast_path` القديم (تجاوز LLM) — يعمل إذا `LONORA_AGENT_FIRST=false`.
3. المسار الخفيف `execute_light_path` (سعر/شارت/متابعة/استبدال).
4. مسار تقرير البوابات `execute_gate_report_path`.
5. الأنبوبة الكاملة: `orchestrator.run_unified_chart_agent` **أو** `kernel.run_trading_kernel` (اثنتان لنفس الغرض).
6. وضع `LONORA_UNIFIED_LOOP ∈ {off, shadow, on}` الذي يغيّر تسجيل الأدوات (`fetch_evidence`, `run_trading_kernel`, `get_gate_report` تظهر فقط عند `on`) وسياسة الخرج.

### 2.4 الشخصيات والتسمية

| الموضع | الشخصية |
|---|---|
| `templates/SOUL.md` L3 | «I am nanobot 🐈» |
| `templates/SOUL.md` L13–19 | قسم «Lonora gold agent» |
| `skills/gold-trading/SKILL.md` | «Lonora Gold Agent — System Constitution» (**غير محقون تلقائياً** — لا مهارة تحمل `always: true`) |
| `agents/synth_prompt.py` | «decision engine» — شخصية ثالثة فعلياً |
| `LONORA_*` env vars (5) | مساحة أسماء تشغيلية |
| `intel/telegram_scraper.py` | اسم جلسة `lonora-news` |

### 2.5 النص العربي داخل `nanobot/`

| الملف | أسطر عربية | الاستخدام | القرار |
|---|---:|---|---|
| `trading/i18n.py` | 365 | نصوص للمستخدم (مراحل، بوابات، بطاقات، رسائل) | **يبقى** لكن يُنقل إلى كتالوج JSON خارج Python |
| `trading/operator_keywords.py` | 31 | **مطابقة نوايا** | **يُحذف** |
| `trading/output_policy.py` | 4 | إعادة كتابة الخرج | **يُحذف** مع المسار الموحد |
| `channels/telegram/tests/test_telegram_channel.py` | 4 | fixtures اختبار | يُنقل إلى fixtures JSON |

وفي `webui/src`: `lib/trading/cardLocale.ts` (36)، `gate-labels.ts` (19)، `stage-labels.ts` (13) — خرائط ثنائية اللغة خارج نظام i18n؛ تُنقل إلى `i18n/locales/ar/*.json`.

### 2.6 «وكلاء يتناقشون» — حقيقي أم لا؟

**حقيقي.** `crew/debate.py` (technical → bull ∥ bear → risk) و`teams/runtime.py` (DAG من YAML) يشغّلان أدواراً عبر `teams/subagent_runner.py` الذي يفضّل `SubagentManager.run_inline` (وكلاء فرعيون LLM فعليون) ثم `provider.chat` مباشرة. البريفات تُغذّي الـ synthesizer ولا يصدر المتناظرون القرار — وهذا صحيح. مشكلتان: (أ) حقل `system_prompt` في `presets/gold_debate_desk.yaml` **لا يُستخدم أبداً** (الأدوار تحصل على `subagent_system.md` العام أو `role_prompts.py` من ~250 حرفاً)؛ (ب) يُستدعى أحياناً آلياً بالكلمات (`_TEAM_PATTERNS`, `_PRESET_BY_KEYWORD`) لا بقرار الوكيل. أما `bots/coordinator.py` فهو ماسح حتمي (ATR/range) وليس نقاشاً.

---

## 3. الهدف المعماري: وكيل واحد، مسار واحد

```
رسالة المشغّل (Web / Mobile / Telegram / WhatsApp)
        │
        ▼
AgentLoop  ← برومبت واحد مركّب (02-prompt-architecture.md)
        │  النموذج يقرأ الرسالة ويقرر الأداة — لا راوتر قبل النموذج
        ▼
أدوات التداول (عقود واضحة، JSON):
  get_gold_quote · fetch_evidence · run_trading_kernel · get_live_recommendation
  manage_trading_plan · capture_gold_chart · run_trading_team · gold_intel_scan
  mt5_propose/confirm/modify/close · create_task/list_tasks (جديد)
        │
        ▼  (داخل run_trading_kernel فقط)
Evidence DAG → Structured Decision Call (نفس هوية الوكيل، عقد خرج JSON) → Gates G1–G20 → Store
        │
        ▼
Artifacts + رد طبيعي بلغة المشغّل   → توزيع متزامن على كل القنوات المفعّلة
```

**قواعد ثابتة (Hard Law) تبقى في الكود لا في البرومبت:** ذهب فقط؛ لا تنفيذ بدون تأكيد بشري؛ البوابات لا تقلب الاتجاه؛ خطة حية واحدة لكل محادثة؛ لا أسعار من الذاكرة؛ عمق spawn = 1.

---

## 4. خطة إزالة الترقيع (De-patching) — مرتبة بالاعتمادية

| # | الإجراء | الملفات | ملاحظات |
|---|---|---|---|
| D1 | تثبيت المسار الموحد كالافتراضي الوحيد: `unified_loop_mode()` يرجع `"on"` دائماً، ثم حذف `LONORA_UNIFIED_LOOP`, `LONORA_AGENT_FIRST`, `LONORA_PLANNER_SHADOW`, `LONORA_UNIFIED_LOOP_SHADOW_SAMPLE` | `trading/config.py`, `agent/loop.py` 1689–1733, `shadow.py`, `tool_delivery.py` | تُستبدل بحقول صريحة في `config/schema.py` عند الحاجة (مثلاً `trading.debug.shadow_log`) |
| D2 | حذف المسار السريع | `agent/loop.py` 1859–1907, `trading/fast_path.py`, `turn_executor.execute_light_path/execute_gate_report_path` | الوكيل يستدعي `get_gold_quote` / `fetch_evidence(['market_data'])` بنفسه |
| D3 | حذف التوجيه بالكلمات | `operator_keywords.py`, `intent_router.py`, `turn_planner.plan_turn` (يبقى `TurnPlan` كبنية بيانات تُملأ من استدعاءات الأدوات لا من regex), `capabilities/planner.py` keyword helpers, `node_planner.py` | تُحذف اختبارات `test_intent_router.py`, `test_fast_path.py` وتُستبدل باختبارات «النموذج اختار الأداة الصحيحة» على fixtures محادثة |
| D4 | توحيد الأنبوبتين | دمج `orchestrator.run_unified_chart_agent` في `kernel.run_trading_kernel` (أو العكس) بحيث يبقى **مدخل واحد** تستدعيه أداة `analyze_gold` = `run_trading_kernel` | `analyze_gold` يصبح alias مهجوراً ثم يُحذف |
| D5 | تسجيل أدوات التداول دائماً | `agent/tools/trading_kernel.py`, `trading_evidence.py` — إزالة شرط `enabled()` المرتبط بـ `unified_loop_serving()` | |
| D6 | الفرق كأدوات فقط | `run_trading_team` يُستدعى من الوكيل فقط؛ حذف `_TEAM_PATTERNS`/`_PRESET_BY_KEYWORD`؛ تمرير `system_prompt` من YAML إلى `run_team_role` فعلياً | `teams/runtime.py`, `teams/subagent_runner.py`, `presets/*.yaml` |
| D7 | شخصية واحدة | حذف قسم Lonora من `templates/SOUL.md`؛ إعادة تسمية المهارة والبرومبت إلى اسم المنتج الواحد (NanoAgent)؛ الـ synthesizer يرث الهوية بالمرجع (02) | `SOUL.md`, `skills/gold-trading/SKILL.md`, `agents/synth_prompt.py`, docstrings, `intel/telegram_scraper.py` |
| D8 | لا عربية في منطق Python | نقل `i18n.py` إلى `nanobot/trading/locales/{ar,en}.json` مع loader صغير `tr()` يحافظ على الواجهة الحالية؛ حذف `output_policy.py` | يبقى `tr(key, locale)` كما هو حتى لا تنكسر الاستدعاءات |
| D9 | نقل الأرقام الثابتة من `policy.py` إلى `TradingRiskParameters` حيث لم تُنقل بعد، والنصوص الثابتة (أسماء presets، أسماء nodes) إلى `catalog` معلن | `trading/policy.py`, `capabilities/catalog.py` | |
| D10 | تخفيف الحجب الصلب في `AnalyzeGoldTool` (الخطة الحية) إلى **خطأ أداة واضح** يعيده الوكيل للمشغّل، لا منع مسبق للنموذج | `agent/tools/trading_chart.py` | |

### معايير القبول

- `rg "[\u0600-\u06FF]" nanobot/ --glob '!**/locales/**' --glob '!**/tests/fixtures/**'` → لا نتائج.
- `rg "LONORA_" nanobot/` → لا نتائج.
- `rg "re.compile" nanobot/trading/ | rg -v "geometry|intel/regex_emergency|calendar"` → لا راوترات نوايا.
- سيناريوهات اختبار محادثة (fixtures) تثبت أن النموذج يختار الأداة الصحيحة لـ: سعر، تحليل، متابعة، صورة شارت، فريق، سؤال عام — بدون أي regex.
- `pytest tests/trading -q` أخضر؛ `basedpyright` بدون أخطاء جديدة.

---

## 5. ما **لا** نحذفه (ولماذا)

| المكوّن | السبب |
|---|---|
| `run_final_decision_synthesizer` + `synth_prompt.py` | استدعاء مبنيّ (JSON schema) هو الطريقة الوحيدة لضمان «كل سعر من قائمة الأدلة» و«لا WAIT تحليلي». يبقى **كأداة داخلية للوكيل الواحد** بنفس الهوية، لا كشخصية ثانية |
| Gates G1–G20 + `gates/execution.py` | قانون سلامة حتمي؛ لا يجوز تركه للبرومبت |
| `recommendations/state_machine.py`, `store.py` | خطة حية واحدة/محادثة |
| `evidence/` DAG | يتيح للوكيل طلب مجموعة فرعية من الأدلة (`fetch_evidence`) بدلاً من الأنبوبة الكاملة |
| `crew/`, `teams/` | «وكلاء يتناقشون» — حقيقي ويعمل؛ يحتاج فقط ربط `system_prompt` وإزالة الاستدعاء بالكلمات |
| `i18n` كمحتوى | يُنقل من Python إلى JSON، لا يُحذف |
