#!/usr/bin/env python3
"""Apply professional Arabic UI strings for keys that must not remain English."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generate_ar_locale import OVERRIDES, flatten, unflatten

AR_PATH = ROOT / "src/i18n/locales/ar/common.json"

LEAK_FIXES: dict[str, str] = {
    "settings.sidebar.title": "الإعدادات",
    "settings.nav.overview": "نظرة عامة",
    "settings.nav.appearance": "المظهر",
    "settings.nav.models": "النماذج",
    "settings.nav.providers": "مزودو الخدمة",
    "settings.nav.apps": "التطبيقات",
    "settings.nav.automations": "المهام المجدولة",
    "settings.nav.runtime": "النظام",
    "settings.nav.advanced": "متقدم",
    "sidebar.automations": "المهام المجدولة",
    "settings.automations.filters.active": "نشط",
    "settings.automations.queue": "قائمة الانتظار",
    "settings.automations.labels.schedule": "الجدولة",
    "settings.automations.status.active": "نشط",
    "settings.sections.interface": "الواجهة",
    "settings.sections.webBehavior": "السلوك",
    "settings.sections.capabilities": "القدرات",
    "settings.sections.apps": "التطبيقات",
    "settings.skills.installedTab": "المثبتة",
    "settings.skills.discoverTab": "استكشاف",
    "settings.skills.customGroup": "مخصصة",
    "settings.skills.builtinGroup": "مدمجة",
    "settings.skills.otherGroup": "أخرى",
    "settings.skills.filterAll": "الكل",
    "settings.skills.filterEnabled": "مفعّلة",
    "settings.skills.filterDisabled": "معطّلة",
    "settings.skills.statusDisabled": "معطّل",
    "settings.skills.statusEnabled": "مفعّل",
    "settings.skills.deleteAction": "حذف",
    "settings.skills.marketplaceSearching": "جارٍ البحث…",
    "settings.skills.marketplaceProviderAll": "الكل",
    "settings.skills.marketplaceInstalling": "جارٍ التثبيت…",
    "settings.skills.marketplaceInstalled": "مثبت",
    "settings.skills.marketplaceInstall": "تثبيت",
    "settings.nanobotFeatures.disable": "تعطيل",
    "settings.nanobotFeatures.ready": "جاهز",
    "settings.sections.about": "حول",
    "settings.rows.theme": "السمة",
    "settings.rows.language": "اللغة",
    "settings.values.light": "فاتح",
    "settings.values.dark": "داكن",
    "settings.values.expanded": "موسّع",
    "settings.values.enabled": "مفعّل",
    "settings.values.disabled": "معطّل",
    "settings.values.configured": "مكوّن",
    "settings.actions.save": "حفظ",
    "settings.actions.saving": "جارٍ الحفظ…",
    "settings.channels.advanced": "متقدم",
    "settings.channels.checkOnly": "فحص",
    "settings.channels.filterAll": "الكل",
    "settings.channels.filterOn": "يعمل",
    "settings.channels.instanceConfigured": "مكوّن",
    "settings.channels.optional": "اختياري",
    "settings.channels.providerPreset": "المزود",
    "settings.channels.savedSecret": "محفوظ",
    "chat.pin": "تثبيت",
    "chat.unpin": "إلغاء التثبيت",
    "chat.rename": "إعادة تسمية",
    "chat.renameSave": "حفظ",
    "chat.archive": "أرشفة",
    "chat.unarchive": "إلغاء الأرشفة",
    "chat.groups.pinned": "مثبتة",
    "chat.groups.projects": "المشاريع",
    "chat.groups.today": "اليوم",
    "chat.groups.yesterday": "أمس",
    "chat.groups.earlier": "سابقًا",
    "chat.groups.archived": "مؤرشفة",
    "workbench.detachPane": "إزالة",
    "settings.channels.open": "فتح",
    "recovery.dismiss": "تجاهل",
    "recovery.continue": "متابعة",
    "connection.open": "متصل",
    "settings.models.fallbackNumber": "بديل {{number}}",
    "settings.mcp.manageTitle": "إدارة {{name}}",
    "settings.automations.schedule.at": "في {{time}}",
    "settings.skills.deleteConfirmTitle": "حذف {{name}}؟",
    "chat.selectedCount": "تم تحديد {{count}}",
    "deleteConfirm.next.label": "التالي: {{time}}",
    "thread.composer.voice.recordingStatus": "جارٍ التسجيل {{time}}",
    "message.skill": "مهارة: {{name}}",
    "message.fileEditDiffLineCount": "{{count}} أسطر",
    "workbench.tabAria": "مجموعة: {{title}}",
    "workbench.composerAria": "رسالة {{title}}",
}

# Remove mistaken duplicate keys that belong under settings.providers only.
REMOVE_PATHS = {
    "chat.open",
    "settings.byok.claudeCodeToken",
    "settings.byok.claudeCodeConnectTitle",
    "settings.byok.claudeCodeConnectHelp",
    "settings.byok.claudeCodeConnectDialogHelp",
    "settings.byok.claudeCodeAuthCode",
    "settings.byok.claudeCodeTokenHelp",
    "settings.byok.claudeCodeTokenConfigured",
    "settings.byok.claudeCodeTokenRequired",
}


def main() -> None:
    ar = json.loads(AR_PATH.read_text(encoding="utf-8"))
    flat = flatten(ar)
    for path in REMOVE_PATHS:
        flat.pop(path, None)
    for path, value in {**OVERRIDES, **LEAK_FIXES}.items():
        flat[path] = value
    AR_PATH.write_text(
        json.dumps(unflatten(flat), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
