#!/usr/bin/env python3
"""Repair corrupted brand placeholders in ar/common.json without re-translating."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generate_ar_locale import KEEP_ENGLISH, OVERRIDES, flatten, unflatten

EN_PATH = ROOT / "src/i18n/locales/en/common.json"
AR_PATH = ROOT / "src/i18n/locales/ar/common.json"
CORRUPTED = re.compile(r"(__KEEP|⟦|NBTOK|NB TOK)")


def terms_in_order(text: str) -> list[str]:
    return [match.group(0) for match in KEEP_ENGLISH.finditer(text)]


def repair_value(en_value: str, ar_value: str) -> str:
    terms = terms_in_order(en_value)
    repaired = ar_value

    def replace_indexed(match: re.Match[str]) -> str:
        index = int(match.group(1))
        return terms[index] if index < len(terms) else match.group(0)

    repaired = re.sub(r"⟦[^⟧]*⟧\s*K(\d+)", replace_indexed, repaired)
    repaired = re.sub(r"⟦⟧[^K]*K(\d+)", replace_indexed, repaired)
    repaired = re.sub(r"NB\s*TOK\s*(\d+)", replace_indexed, repaired)
    repaired = re.sub(r"__KEEP\s*_?(\d+)__", replace_indexed, repaired)
    repaired = re.sub(r"⟦K(\d+)⟧", replace_indexed, repaired)
    repaired = re.sub(r"([{]{2}\s*\w+)\s*⟦\s*([}]{2})", r"\1\2", repaired)
    repaired = re.sub(r"⟧\s*", " ", repaired)
    repaired = re.sub(r"\s*⟦", " ", repaired)
    repaired = repaired.replace("⟧", "").replace("⟦", "")

    for index, term in enumerate(terms):
        for pattern in (
            f"NBTOK{index}",
            f"⟦⟧ K{index}",
            f"K{index}",
        ):
            if pattern == f"K{index}":
                repaired = re.sub(rf"\bK{index}\b", term, repaired)
            else:
                repaired = repaired.replace(pattern, term)

    repaired = re.sub(r"\s+", " ", repaired).strip()
    return repaired


def main() -> None:
    import time

    from deep_translator import MyMemoryTranslator
    from scripts.generate_ar_locale import post_process, protect_terms, restore_terms, translate_batch

    en = json.loads(EN_PATH.read_text(encoding="utf-8"))
    ar = json.loads(AR_PATH.read_text(encoding="utf-8"))
    flat_en = flatten(en)
    flat_ar = flatten(ar)
    translator = MyMemoryTranslator(source="en-GB", target="ar-SA")

    for path, value in OVERRIDES.items():
        flat_ar[path] = value

    fixed = 0
    for path, en_value in flat_en.items():
        ar_value = flat_ar.get(path, "")
        if path in OVERRIDES:
            continue
        if not CORRUPTED.search(ar_value):
            continue
        flat_ar[path] = repair_value(en_value, ar_value)
        fixed += 1

    remaining = [path for path, value in flat_ar.items() if CORRUPTED.search(value)]
    AR_PATH.write_text(
        json.dumps(unflatten(flat_ar), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"repaired {fixed} strings; remaining corrupted: {len(remaining)}")
    if remaining:
        print("\n".join(remaining[:20]))


if __name__ == "__main__":
    main()
