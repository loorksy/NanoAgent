"""Operator rules sit after Hard Law. ``allow`` cannot reverse a denial."""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Literal

from mokli.agent_api.events import approval_data
from mokli.config_base import Base
from mokli.security.secret_store import SecretStore, SecretStoreError, get_secret_store
from mokli.trading.policy_guard import PolicyViolation
from mokli.trading.turn_session import current_turn_session

RuleDecision = Literal["allow", "approve", "deny"]
RULE_KEYS = ("propose_order", "room_message", "external_message", "python", "web")
DESK_RULES_SECRET = "desk_rules"

_TOOL_ACTIONS = {
    "mt5_propose_order": "propose_order",
    "send_session_message": "room_message",
    "message": "external_message",
    "run_python": "python",
    "web_fetch": "web",
}

_RULES: ContextVar["DeskRules | None"] = ContextVar("mokli_desk_rules", default=None)
_GRANTS: set[str] = set()
_GRANT_LOCK = threading.Lock()


class DeskRules(Base):
    propose_order: RuleDecision = "approve"
    room_message: RuleDecision = "allow"
    external_message: RuleDecision = "approve"
    python: RuleDecision = "allow"
    web: RuleDecision = "allow"
    updated_by: str = ""

    def decision_for(self, action: str) -> RuleDecision:
        if action not in RULE_KEYS:
            raise KeyError(action)
        value = getattr(self, action)
        return value


class ApprovalRequired(Exception):  # noqa: N818 — operator hold, not a failure
    """The tool must not run until the operator confirms the existing approval card."""

    def __init__(self, action: str, tool_name: str) -> None:
        super().__init__(f"Operator approval required for {action}")
        self.action = action
        self.tool_name = tool_name

    def gateway_event(self) -> dict[str, object]:
        return approval_data(
            f"desk-{self.action}",
            type=self.action,
            summary=f"Approve {self.tool_name}",
            expires_at=None,
            status="pending",
        )


class DeskRuleStore:
    """Persist rules beside MT5 permissions. Tests pass an in-memory secret stand-in."""

    def __init__(self, secrets: SecretStore | object | None = None) -> None:
        self._secrets = secrets
        self._lock = threading.RLock()

    @property
    def secrets(self) -> SecretStore | object:
        return self._secrets if self._secrets is not None else get_secret_store()

    def load(self) -> DeskRules:
        with self._lock:
            try:
                raw = self.secrets.get(DESK_RULES_SECRET)  # type: ignore[attr-defined]
            except (SecretStoreError, OSError, AttributeError):
                return DeskRules()
        if not raw:
            return DeskRules()
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                return DeskRules()
            return DeskRules.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            return DeskRules()

    def save(self, rules: DeskRules, *, who: str) -> DeskRules:
        stored = rules.model_copy(update={"updated_by": who or "operator"})
        payload = json.dumps(stored.model_dump(mode="json"), sort_keys=True)
        with self._lock:
            self.secrets.set(DESK_RULES_SECRET, payload)  # type: ignore[attr-defined]
        return stored


_default_store: DeskRuleStore | None = None


def get_rule_store() -> DeskRuleStore:
    global _default_store
    if _default_store is None:
        _default_store = DeskRuleStore()
    return _default_store


def set_rule_store(store: DeskRuleStore | None) -> None:
    global _default_store
    _default_store = store


def active_rules() -> DeskRules:
    override = _RULES.get()
    if override is not None:
        return override
    try:
        return get_rule_store().load()
    except (SecretStoreError, OSError):
        return DeskRules()


@contextmanager
def rules_scope(rules: DeskRules):
    token: Token[DeskRules | None] = _RULES.set(rules)
    try:
        yield rules
    finally:
        _RULES.reset(token)


def rule_action_for(tool_name: str, session_key: str | None) -> str | None:
    action = _TOOL_ACTIONS.get(tool_name)
    if action == "room_message" and not (session_key or "").startswith("desk:"):
        return None
    return action


def grant_action(action: str) -> None:
    """Allow the next call of an approve-rule action. One call, then it holds again."""
    if action not in RULE_KEYS:
        raise KeyError(action)
    with _GRANT_LOCK:
        _GRANTS.add(action)


def _consume_grant(action: str) -> bool:
    with _GRANT_LOCK:
        if action not in _GRANTS:
            return False
        _GRANTS.remove(action)
        return True


def apply_operator_rule(tool_name: str, session_key: str | None) -> None:
    """Deny or hold. ``allow`` returns so later gates still run."""
    action = rule_action_for(tool_name, session_key)
    if action is None:
        return
    decision = active_rules().decision_for(action)
    if decision == "deny":
        raise PolicyViolation(f"Operator rule denied {action}")
    if decision == "approve" and not _consume_grant(action):
        raise ApprovalRequired(action, tool_name)


def hold_for_approval(exc: ApprovalRequired) -> dict[str, object]:
    event = exc.gateway_event()
    turn = current_turn_session()
    if turn is not None:
        turn.pending_approvals.append(event)
    return event


def rules_from_payload(payload: dict[str, object], *, who: str) -> DeskRules:
    data = {key: payload[key] for key in RULE_KEYS if key in payload}
    data["updated_by"] = who
    return DeskRules.model_validate(data)
