#!/usr/bin/env python3
"""Generate ar/common.json from en/common.json with professional Arabic localization."""

from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from deep_translator import MyMemoryTranslator

ROOT = Path(__file__).resolve().parents[1]
EN_PATH = ROOT / "src/i18n/locales/en/common.json"
AR_PATH = ROOT / "src/i18n/locales/ar/common.json"
BATCH_SIZE = 15
WORKERS = 4
SLEEP_SECONDS = 0.2

# Preserve brand names, product terms, and interpolation placeholders.
KEEP_ENGLISH = re.compile(
    r"\b("
    r"nanobot|Claude|Telegram|WhatsApp|TradingView|XAUUSD|OAuth|MCP|API|CLI|JSON|"
    r"GitHub|Slack|Discord|Matrix|OpenAI|Anthropic|Azure|Bedrock|"
    r"BotFather|@BotFather|Linked devices|"
    r"CLAUDE_CODE_OAUTH_TOKEN|setup-token"
    r")\b",
    re.IGNORECASE,
)

# Manual overrides for professional mixed ar/en copy (path -> value).
OVERRIDES: dict[str, str] = {
    "app.loading.boot": "جارٍ تحميل nanobot…",
    "app.loading.connecting": "جارٍ الاتصال بـ nanobot…",
    "app.meta.description": "واجهة nanobot — تحدّث مع مساحة عمل nanobot.",
    "settings.providers.claudeCodeToken": "رمز Claude Code CLI",
    "settings.providers.claudeCodeConnectTitle": "حساب Claude",
    "settings.providers.claudeCodeConnectHelp": (
        "افتح Claude في هذا المتصفح لربط اشتراكك. يخزّن NanoAgent CLAUDE_CODE_OAUTH_TOKEN "
        "بنفس طريقة لصق setup-token."
    ),
    "settings.providers.claudeCodeConnectDialogHelp": (
        "أكمل تسجيل الدخول في صفحة Claude. ستظهر لك رمز (غالباً code#state). "
        "الصقه هنا — Anthropic لا يعيد التوجيه إلى هذا الموقع."
    ),
    "settings.providers.claudeCodeAuthCode": "رمز التفويض من Claude",
    "settings.providers.claudeCodeTokenHelp": (
        "أو الصق CLAUDE_CODE_OAUTH_TOKEN من `claude setup-token` إن كان لديك واحد. "
        "يقرأ Claude CLI الرسمي هذا المتغير في الاستدعاء التالي."
    ),
    "settings.providers.claudeCodeTokenConfigured": "متصل · آخر 4 أرقام {{hint}}",
    "settings.providers.claudeCodeTokenRequired": "الصق رمز Claude Code CLI غير فارغ.",
    "settings.mcp.connected": "متصل",
    "settings.channels.validation.connected": "متصل",
    "connection.open": "متصل",
    "trading.chart.title": "رسم الذهب",
    "trading.chart.subtitle": "XAUUSD · TradingView Advanced Charts · اطلب من الوكيل تحليل الذهب في المحادثة",
    "trading.chart.analyze": "تحليل الذهب",
    "trading.chart.analyzing": "جارٍ التحليل…",
    "trading.chart.liveMarket": "سوق حي",
    "trading.chart.marketUnavailable": "بيانات السوق غير متاحة",
    "trading.connect.title": "ربط Telegram و WhatsApp",
    "trading.connect.whatsappQr.connected": "WhatsApp متصل.",
    "trading.connect.subtitle": (
        "الصق رمز بوت Telegram من @BotFather، أو امسح رمز QR لـ WhatsApp. "
        "هذه شاشة الإعداد الوحيدة — بدون خطوات تثبيت إضافية."
    ),
    "trading.connect.whatsappQr.scanDescription": (
        "في WhatsApp، افتح الأجهزة المرتبطة، اختر ربط جهاز، ثم امسح هذا الرمز."
    ),
}


def flatten(obj: Any, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            out.update(flatten(value, path))
    elif isinstance(obj, str):
        out[prefix] = obj
    else:
        raise TypeError(f"Unexpected value at {prefix}: {type(obj)}")
    return out


def unflatten(flat: dict[str, str]) -> dict[str, Any]:
    root: dict[str, Any] = {}
    for path, value in flat.items():
        parts = path.split(".")
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return root


def protect_terms(text: str) -> tuple[str, list[tuple[str, str]]]:
    replacements: list[tuple[str, str]] = []
    protected = text

    def repl(match: re.Match[str]) -> str:
        token = f"NBTOK{len(replacements)}"
        replacements.append((token, match.group(0)))
        return token

    protected = KEEP_ENGLISH.sub(repl, protected)
    return protected, replacements


def restore_terms(text: str, replacements: list[tuple[str, str]]) -> str:
    for index, (token, original) in enumerate(replacements):
        text = text.replace(token, original)
        # Recover common MyMemory corruption patterns for older runs.
        for pattern in (
            token,
            token.replace("NBTOK", "NB TOK "),
            token.replace("NBTOK", "NBTOK "),
            f"__KEEP _{index}__",
            f"⟦K{index}⟧",
            f"⟦⟧ K{index}",
        ):
            text = text.replace(pattern, original)
    return text


def post_process(path: str, text: str) -> str:
    if path in OVERRIDES:
        return OVERRIDES[path]
    # Normalize ellipsis
    text = text.replace("...", "…")
    # Avoid awkward literal "تم الاتصال" for simple Connected labels in short UI chrome
    if path.endswith(".connected") and text.startswith("تم الاتصال"):
        text = "متصل"
    # MyMemory sometimes translates the brand literally
    text = re.sub(r"آلة مجهرية[^.\n]*نانو[^.\n]*", "nanobot", text)
    text = re.sub(r"روبوت نانو\b", "nanobot", text)
    return text


def should_skip_translation(value: str) -> bool:
    stripped = value.strip()
    if stripped in {"nanobot", "XAUUSD"}:
        return True
    return bool(re.fullmatch(r"[\w@./:#\-{}]+", stripped))


def translate_batch(translator: MyMemoryTranslator, texts: list[str]) -> list[str]:
    for attempt in range(5):
        try:
            return translator.translate_batch(texts)
        except Exception:
            time.sleep(2 ** attempt)
    raise RuntimeError("Translation failed after retries")


def translate_chunk(
    chunk: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    translator = MyMemoryTranslator(source="en-GB", target="ar-SA")
    out: list[tuple[str, str]] = []
    batch_paths: list[str] = []
    batch_values: list[str] = []
    batch_meta: list[list[tuple[str, str]]] = []

    for path, value in chunk:
        if should_skip_translation(value):
            out.append((path, post_process(path, value)))
            continue
        protected, meta = protect_terms(value)
        batch_paths.append(path)
        batch_values.append(protected)
        batch_meta.append(meta)

    if batch_values:
        batch_out = translate_batch(translator, batch_values)
        for path, raw, meta in zip(batch_paths, batch_out, batch_meta, strict=True):
            restored = restore_terms(raw, meta)
            out.append((path, post_process(path, restored)))
        time.sleep(SLEEP_SECONDS)
    return out


def main() -> None:
    en = json.loads(EN_PATH.read_text(encoding="utf-8"))
    flat_en = flatten(en)
    paths = list(flat_en.keys())
    values = [flat_en[p] for p in paths]
    items = list(zip(paths, values, strict=True))
    chunks = [items[i : i + BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]

    translated_map: dict[str, str] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(translate_chunk, chunk): chunk for chunk in chunks}
        for future in as_completed(futures):
            for path, value in future.result():
                translated_map[path] = value
            done += 1
            print(f"Translated chunk {done}/{len(chunks)}", flush=True)

    flat_ar = {path: translated_map[path] for path in paths}
    AR_PATH.parent.mkdir(parents=True, exist_ok=True)
    AR_PATH.write_text(
        json.dumps(unflatten(flat_ar), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {AR_PATH} ({len(flat_ar)} strings)")


if __name__ == "__main__":
    main()
