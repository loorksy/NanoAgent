---
name: mokli-upgrade
description: ترقية وكيل Mokli — كفاءة التوكن، قياس التأخير، نشاط حقيقي من أحداث وقت التشغيل، ووكلاء التداول. استخدمه proactively عند طلب تدقيق السياق أو حلقة الأدوات أو نشاط الواجهة أو قرار التداول المنظم.
---

أنت تعمل داخل مستودع Mokli الحالي. الكود هو مصدر الحقيقة. لا تبنِ نظاماً موازياً (ممنوع AgentRunner2 أو ToolRegistry2 أو Memory2 أو TradingKernel2 أو StrategyEngine2). طوّر الموجود.

## مسار الطلب

المستخدم → أنبوب Mokli في الواجهة → Agent API → AgentLoop → AgentRunner → مزود النموذج → الأدوات → نتيجة الأداة تُلحَق بالسجل → الطلب التالي يعيد إرسال السياق. نشاط الواجهة يأتي من أحداث `tool` و`state` و`subagent` فقط.

## قواعد لا تُكسر

- لا سقف max_tokens ثابت، ولا قص عشوائي للسجل، ولا حذف رسائل قديمة كعلاج للتوكن.
- كل سطر في نشاط الوكيل يقابله حدث حقيقي. ممنوع setTimeout أو مراحل وهمية أو اسم أداة خام في السطر الرئيسي.
- وصف العرض يأتي من بيانات الأداة (`mokli/agent/tools/display.py`) لا من تفريع على الاسم داخل الواجهة.
- الأدوات المستقلة والمتزامنة فقط تُنفَّذ بالتوازي. لا تتجاوز طبقة المخاطر أو تشغّل كود النموذج على حساب حقيقي.
- وكلاء التداول يمرون عبر `run_trading_team` و`SubagentManager` والـ presets، ثم `run_trading_kernel` للقرار. لا محرك فريق ثانٍ.
- قِس قبل وبعد: توكن الإدخال، حجم نتائج الأدوات، عدد الدورات، زمن النموذج مقابل زمن الأدوات.

## أين تضع الإصلاح

- طيّ نتائج الأدوات السابقة: `mokli/agent/context_governance.py`
- القياس: `mokli/agent/turn_diagnostics.py` و`AgentRunner`
- منع إعادة الأداة للقراءة فقط داخل الطلب نفسه: `mokli/agent/tools/execution.py`
- طبقات السياق: `mokli/agent/context_layers.py` و`ContextBuilder`
- نص الواجهة: أحداث Agent API ثم `deploy/mokliui/functions/mokli_pipe.py`
- شاشة المطور: صمام `SHOW_DIAGNOSTICS` وحدث `diagnostic`
