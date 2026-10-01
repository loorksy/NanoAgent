"""Child entrypoint for ``run_python``.

This file runs inside the sandbox process. It applies resource limits, blocks
new sockets, then executes the reviewed program with a reduced builtin set.
It is not a tool the model calls.
"""

from __future__ import annotations

import builtins
import resource
import sys

ALLOWED_MODULES = frozenset(
    {
        "math",
        "statistics",
        "json",
        "decimal",
        "datetime",
        "collections",
        "itertools",
        "functools",
        "re",
    }
)

_SAFE_BUILTIN_NAMES = (
    "abs",
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "filter",
    "float",
    "int",
    "isinstance",
    "len",
    "list",
    "map",
    "max",
    "min",
    "pow",
    "print",
    "range",
    "repr",
    "reversed",
    "round",
    "set",
    "slice",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
    "Exception",
    "ValueError",
    "TypeError",
    "ZeroDivisionError",
    "StopIteration",
    "ArithmeticError",
    "AssertionError",
    "IndexError",
    "KeyError",
    "OverflowError",
)


def _block_network() -> None:
    import socket

    def _refused(*_args: object, **_kwargs: object) -> object:
        raise OSError("network is disabled")

    class _Blocked(socket.socket):
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise OSError("network is disabled")

    socket.socket = _Blocked  # type: ignore[misc]
    socket.create_connection = _refused  # type: ignore[assignment]
    socket.create_server = _refused  # type: ignore[assignment]
    try:
        socket.create_connection(("127.0.0.1", 9), timeout=0.2)
    except OSError:
        return
    raise SystemExit("network block failed")


def _safe_import(
    name: str,
    globals: object = None,
    locals: object = None,
    fromlist: tuple[str, ...] = (),
    level: int = 0,
) -> object:
    root = name.split(".", 1)[0]
    if level or root not in ALLOWED_MODULES:
        raise ImportError(f"import blocked: {name}")
    return builtins.__import__(name, globals, locals, fromlist, level)  # type: ignore[arg-type]


def main() -> None:
    source_path = sys.argv[1]
    memory_bytes = int(sys.argv[2])
    cpu_seconds = int(sys.argv[3])
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1_000_000, 1_000_000))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    _block_network()
    source = open(source_path, encoding="utf-8").read()
    safe: dict[str, object] = {name: getattr(builtins, name) for name in _SAFE_BUILTIN_NAMES}
    safe["True"] = True
    safe["False"] = False
    safe["None"] = None
    safe["__import__"] = _safe_import
    exec(compile(source, "<sandbox>", "exec"), {"__builtins__": safe})  # noqa: S102


if __name__ == "__main__":
    main()
