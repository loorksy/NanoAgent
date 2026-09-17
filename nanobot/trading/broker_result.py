"""Decide whether a MetaAPI / MT5 transport payload is a real broker success.

Propose/confirm must not mark a proposal executed, and must not open a Ticket,
unless the transport returned a successful broker result.
"""

from __future__ import annotations

from typing import Any

from nanobot.trading.i18n import tr

# MetaTrader 5 success retcodes used by MetaAPI:
# 10008 TRADE_RETCODE_PLACED, 10009 TRADE_RETCODE_DONE, 10010 DONE_PARTIAL.
_SUCCESS_RETCODES = {10008, 10009, 10010}


def _as_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    return None


def _numeric_code(result: dict[str, Any]) -> int | None:
    raw = result.get("numericCode", result.get("numeric_code"))
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _string_code(result: dict[str, Any]) -> str:
    return str(result.get("stringCode") or result.get("string_code") or "").upper()


def _ticket_id(result: dict[str, Any] | None, sent: dict[str, Any]) -> str | None:
    if result is not None:
        for key in ("positionId", "position_id", "orderId", "order_id", "id"):
            value = result.get(key)
            if value is not None and str(value).strip():
                return str(value)
    for key in ("position_id", "order_id", "id"):
        value = sent.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return None


def broker_send_succeeded(sent: Any, *, require_ticket: bool = False) -> bool:
    """Return True only when the transport reports a successful broker action."""
    payload = _as_dict(sent)
    if payload is None:
        return False
    if payload.get("ok") is False:
        return False
    error = payload.get("error")
    if error:
        return False
    result = payload.get("result")
    if result is None:
        return False
    result_dict = _as_dict(result)
    if result_dict is not None:
        if result_dict.get("error"):
            return False
        numeric = _numeric_code(result_dict)
        if numeric is not None and numeric not in _SUCCESS_RETCODES:
            return False
        code = _string_code(result_dict)
        if code and "RETCODE" in code and not any(
            token in code for token in ("DONE", "PLACED")
        ):
            return False
        if require_ticket and _ticket_id(result_dict, payload) is None:
            return False
        return True
    if require_ticket:
        return False
    return bool(result)


def broker_error_message(sent: Any) -> str:
    payload = _as_dict(sent) or {}
    error = payload.get("error")
    if error:
        return str(error)
    result = _as_dict(payload.get("result")) or {}
    for key in ("message", "stringCode", "string_code", "description"):
        value = result.get(key)
        if value:
            return str(value)
    return tr("mt5.broker_rejected")


def wrap_sdk_result(result: Any) -> dict[str, Any]:
    """Normalize a MetaAPI SDK return value into ``{ok, result, error?}``."""
    if result is None:
        return {"ok": False, "error": tr("mt5.empty_broker_result"), "result": None}
    result_dict = _as_dict(result)
    payload = {"ok": True, "result": result}
    if result_dict is not None and not broker_send_succeeded(payload):
        return {
            "ok": False,
            "error": broker_error_message(payload),
            "result": result,
        }
    if not broker_send_succeeded(payload):
        return {"ok": False, "error": tr("mt5.invalid_broker_result"), "result": result}
    return payload


def position_ticket(sent: dict[str, Any]) -> str | None:
    result = _as_dict(sent.get("result"))
    return _ticket_id(result, sent)
