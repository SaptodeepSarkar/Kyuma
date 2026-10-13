"""Phase 07 — exec dispatcher. Validates Exec, routes to capability handlers.

Later phases (08-13) replace stubs via register_handler() without touching dispatch().
Never raises: all failures become error Results.
"""
from __future__ import annotations

from typing import Any, Callable

from harness.contracts import ACTIONS, Exec, Result

Handler = Callable[[dict[str, Any]], Result]


def _stub(action: str) -> Handler:
    def handle(args: dict[str, Any]) -> Result:
        return Result(code=200, detail=f"{action} stub ok")

    handle.__name__ = f"stub_{action}"
    return handle


HANDLERS: dict[str, Handler] = {a: _stub(a) for a in ACTIONS}


def register_handler(action: str, fn: Handler) -> None:
    """Plug in a real capability (phases 08-13). Raises only on bad registration."""
    if action not in ACTIONS:
        raise ValueError(f"unknown action: {action!r}")
    if not callable(fn):
        raise TypeError("handler must be callable")
    HANDLERS[action] = fn


def dispatch(exec_like: Any) -> Result:
    """Validate exec_like -> route -> Result. Never raises."""
    try:
        exec_ = exec_like if isinstance(exec_like, Exec) else Exec.from_dict(exec_like)
    except Exception as e:
        return Result(code="error", detail=f"invalid Exec: {e}")
    handler = HANDLERS.get(exec_.action)
    if handler is None:
        return Result(code="error", detail=f"unknown action: {exec_.action!r}")
    try:
        res = handler(exec_.args)
    except Exception as e:
        return Result(code="error", detail=f"handler {exec_.action} crashed: {e}")
    if not isinstance(res, Result):
        return Result(code="error", detail=f"handler {exec_.action} returned bad type")
    return res
