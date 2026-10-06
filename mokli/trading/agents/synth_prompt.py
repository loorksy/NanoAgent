"""Structured-decision system prompt, loaded from ``mokli/agent/prompt/decision_contract.md``."""

from __future__ import annotations

from mokli.agent.prompt.composer import (
    DEFAULT_PRODUCT_NAME,
    compose_decision_prompt,
    decision_contract_template,
)

SYNTH_SYSTEM_PROMPT = decision_contract_template()


def synth_system_prompt(language: str, *, product_name: str = DEFAULT_PRODUCT_NAME) -> str:
    """Decision contract rendered for ``language`` plus the inherited hard law layer."""
    return compose_decision_prompt(language=language, product_name=product_name)
