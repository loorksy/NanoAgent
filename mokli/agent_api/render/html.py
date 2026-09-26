"""Jinja2 rendering of structured results; labels resolved through :class:`Labels`."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from mokli.agent_api.labels import Labels
from mokli.agent_api.results import ResultRecord

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


@cache
def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(default=True, default_for_string=True),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["num"] = format_number
    env.filters["pct"] = format_percent
    return env


def format_number(value: object, digits: int = 2) -> str:
    if isinstance(value, bool) or value is None:
        return "—"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    return str(value)


def format_percent(value: object) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{float(value) * 100:.0f}%"
    return "—"


def template_name(result_type: str) -> str:
    return f"{result_type}.html"


def render_result_html(result: ResultRecord, locale: str | None) -> str:
    labels = Labels(locale)
    template = _environment().get_template(template_name(result["type"]))
    return template.render(
        L=labels,
        labels=labels,
        dir=labels.dir,
        locale=labels.locale,
        type=result["type"],
        result_id=result["id"],
        ts=result["ts"],
        p=result["payload"],
    )
