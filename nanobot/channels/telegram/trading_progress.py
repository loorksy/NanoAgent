"""Arabic Telegram progress bubble for gold trading stages."""

from __future__ import annotations

from dataclasses import dataclass, field

from nanobot.trading.stage_events import STAGE_LABEL_AR, StageEvent, stage_label

TRADING_PROGRESS_META = "trading_progress"
TRADING_CARD_SENT_META = "trading_card_sent"
TELEGRAM_TRADING_PROGRESS = TRADING_PROGRESS_META
TELEGRAM_TRADING_CARD_SENT = TRADING_CARD_SENT_META


@dataclass
class TelegramStageRow:
    stage: str
    status: str
    notes: list[str] = field(default_factory=list)


def render_arabic_stage_line(stage: str, status: str) -> str:
    mark = "✅" if status == "done" else "❌" if status == "failed" else "⏳"
    label = stage_label(stage, "ar")
    return f"{mark} {label}"


def render_arabic_progress(rows: list[TelegramStageRow]) -> str:
    lines = [render_arabic_stage_line(row.stage, row.status) for row in rows]
    return "\n".join(lines)


def apply_stage_event(rows: list[TelegramStageRow], event: StageEvent) -> list[TelegramStageRow]:
    updated = list(rows)
    for index, row in enumerate(updated):
        if row.stage == event.stage:
            updated[index] = TelegramStageRow(
                stage=event.stage,
                status=event.status,
                notes=row.notes,
            )
            return updated
    updated.append(TelegramStageRow(stage=event.stage, status=event.status))
    return updated


def stage_arabic_label(stage: str) -> str:
    return STAGE_LABEL_AR.get(stage, stage)
