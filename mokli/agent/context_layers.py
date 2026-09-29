"""Choose which prompt layers a turn actually needs.

Durable identity stays. Long-term memory and the skills catalog are task
layers: a short message that is not about trading, memory, or a strategy
does not reload them. Conversation history and fresh tool output stay on
their own path in the runner.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A short greeting or a one-line question has no trading or memory job.
_TASK_MARKERS = re.compile(
    r"ذهب|الذهب|gold|xau|تحليل|استراتيج|strategy|backtest|صفقة|توصية|"
    r"خبر|أخبار|news|macro|ذاكرة|تذكر|تابع|أكمل|اكمل|continue|remember",
    re.IGNORECASE,
)
_SHORT_TURN_CHARS = 280


@dataclass(frozen=True, slots=True)
class ContextLayers:
    include_memory: bool
    include_skills: bool


def layers_for_task(text: str | None) -> ContextLayers:
    body = (text or "").strip()
    if not body or len(body) > _SHORT_TURN_CHARS or _TASK_MARKERS.search(body):
        return ContextLayers(include_memory=True, include_skills=True)
    return ContextLayers(include_memory=False, include_skills=False)
