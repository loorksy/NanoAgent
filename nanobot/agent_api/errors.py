"""Uniform error envelope: ``{"error": {"code", "message_key", "details"}}``."""

from __future__ import annotations

from typing import TypedDict

from aiohttp import web


class ErrorBody(TypedDict):
    code: str
    message_key: str
    details: dict[str, object]


class ErrorEnvelope(TypedDict):
    error: ErrorBody


class ApiError(Exception):
    """Raised by handlers; converted to a JSON response by the error middleware."""

    def __init__(
        self,
        status: int,
        code: str,
        message_key: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.message_key = message_key or code
        self.details: dict[str, object] = dict(details or {})

    def envelope(self) -> ErrorEnvelope:
        return {
            "error": {
                "code": self.code,
                "message_key": self.message_key,
                "details": self.details,
            }
        }

    def response(self) -> web.Response:
        return web.json_response(self.envelope(), status=self.status)


def error_response(
    status: int,
    code: str,
    message_key: str | None = None,
    details: dict[str, object] | None = None,
) -> web.Response:
    return ApiError(status, code, message_key, details).response()


def not_available(feature: str) -> web.Response:
    """501 for capabilities whose backing module is not present in this build."""
    return error_response(501, "not_available", "not_available", {"feature": feature})
