"""Policy-gated Python for calculations. Returns text only."""

from __future__ import annotations

from typing import Any

from mokli.agent.tools.base import Tool, ToolResult
from mokli.agent.tools.schema import IntegerSchema, StringSchema, tool_parameters_schema
from mokli.trading.code_policy import MAX_CODE_CHARS, CodePolicyError
from mokli.trading.python_sandbox import MAX_TIMEOUT_S, run_python_sandbox


class RunPythonTool(Tool):
    """Execute reviewed Python in an isolated process and return stdout/stderr."""

    @property
    def name(self) -> str:
        return "run_python"

    @property
    def description(self) -> str:
        return (
            "Run a short Python calculation and return stdout and stderr only. "
            "The program is reviewed before it starts. It cannot read credentials, "
            "reach the network, import MetaTrader, or place orders. "
            "Allowed imports: math, statistics, json, decimal, datetime, "
            "collections, itertools, functools, re. "
            f"Maximum {MAX_CODE_CHARS} characters and {MAX_TIMEOUT_S} seconds."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(
            code=StringSchema(
                "Python source to review and run",
                min_length=1,
                max_length=MAX_CODE_CHARS,
            ),
            timeout_seconds=IntegerSchema(
                description="Wall-clock limit in seconds",
                minimum=1,
                maximum=MAX_TIMEOUT_S,
            ),
            required=["code"],
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, code: str = "", timeout_seconds: int = 5, **kwargs: Any) -> Any:
        del kwargs
        try:
            result = run_python_sandbox(code, timeout_s=timeout_seconds or 5)
        except CodePolicyError as exc:
            return ToolResult.error(exc.reason)
        rendered = result.render()
        if result.timed_out or result.exit_code != 0:
            return ToolResult.error(rendered)
        return rendered
