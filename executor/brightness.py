"""Phase 12 — brightness via brightnessctl. Import path: ``executor.brightness``.

Backend choice: ``brightnessctl`` is the standard backlight CLI on Arch —
it talks to the kernel backlight class (here: ``nvidia_wmi_ec_backlight``),
needs no root for reads, supports percent + delta sets and machine-readable
output. Rejected: raw ``/sys/class/backlight`` writes (root + device-specific
paths), ``ddcutil`` (external monitors only), ``light`` (unmaintained).

Ops (all take an args dict, return ``harness.contracts.Result``):
- ``handle_brightness_get({})`` → ``200 "brightness NN%"``.
- ``handle_brightness_set({"value": pct})`` — pct int, percent 1–100.
  Out of range → error Result, device untouched.
- ``handle_brightness_up/down({"step": pct})`` — default step STEP_PCT (10%).
- ``handle_brightness(args)`` — dispatcher on ``args["op"]``; registered as
  the ``brightness`` handler via ``register_handler`` (router untouched).

No-blackout guard: plain ``set 0`` is REJECTED (error Result, device
untouched). Full blackout needs the explicit flag ``{"value": 0,
"force": True}``, which passes ``-n 0`` (brightnessctl otherwise clamps
writes to a minimum of 1 by default).
"""
from __future__ import annotations

import subprocess
from typing import Any

from harness.contracts import Result

STEP_PCT = 10
_DEVICE_CLASS = "backlight"


def _ctl(*args: str) -> str:
    """Run brightnessctl on the backlight class; return stdout stripped."""
    try:
        proc = subprocess.run(
            ["brightnessctl", "-c", _DEVICE_CLASS, *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"brightnessctl not runnable: {e}") from e
    if proc.returncode != 0:
        raise RuntimeError(f"brightnessctl {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _percent() -> int:
    """Current brightness as integer percent of device max."""
    try:
        cur = int(_ctl("get"))
        maxv = int(_ctl("max"))
    except (RuntimeError, ValueError) as e:
        raise RuntimeError(f"no backlight device readable: {e}") from e
    if maxv <= 0:
        raise RuntimeError("backlight max is 0, cannot compute percent")
    return round(cur * 100 / maxv)


def handle_brightness_get(args: dict[str, Any]) -> Result:
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    try:
        return Result(code=200, detail=f"brightness {_percent()}%")
    except RuntimeError as e:
        return Result(code="error", detail=str(e))


def _as_pct(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def handle_brightness_set(args: dict[str, Any]) -> Result:
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    pct = _as_pct(args.get("value"))
    if pct is None:
        return Result(code="error", detail="brightness set needs {value: int percent}")
    if pct == 0 and not args.get("force") is True:
        return Result(code="error", detail="refusing brightness 0 without {value: 0, force: true}")
    if not 0 <= pct <= 100:
        return Result(code="error", detail=f"brightness {pct} out of range 0-100")
    try:
        if pct == 0:
            _ctl("-n", "0", "set", "0")  # explicit-flag path only (see module doc)
        else:
            _ctl("set", f"{pct}%")
        return Result(code=200, detail=f"brightness {_percent()}%")
    except RuntimeError as e:
        return Result(code="error", detail=str(e))


def _step(args: dict[str, Any]) -> int | None:
    step = args.get("step", STEP_PCT)
    if isinstance(step, bool) or not isinstance(step, int) or step <= 0:
        return None
    return step


def handle_brightness_up(args: dict[str, Any]) -> Result:
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    step = _step(args)
    if step is None:
        return Result(code="error", detail=f"bad step, need positive int (default {STEP_PCT})")
    try:
        _ctl("set", f"+{step}%")
        return Result(code=200, detail=f"brightness {_percent()}%")
    except RuntimeError as e:
        return Result(code="error", detail=str(e))


def handle_brightness_down(args: dict[str, Any]) -> Result:
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    step = _step(args)
    if step is None:
        return Result(code="error", detail=f"bad step, need positive int (default {STEP_PCT})")
    try:
        _ctl("set", f"{step}%-")
        return Result(code=200, detail=f"brightness {_percent()}%")
    except RuntimeError as e:
        return Result(code="error", detail=str(e))


def handle_brightness(args: dict[str, Any]) -> Result:
    """Dispatcher for dispatch.register_handler("brightness", handle_brightness)."""
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    op = args.get("op", "get")
    if op == "get":
        return handle_brightness_get(args)
    if op == "set":
        return handle_brightness_set(args)
    if op == "up":
        return handle_brightness_up(args)
    if op == "down":
        return handle_brightness_down(args)
    return Result(code="error", detail=f"unknown brightness op: {op!r} (get|set|up|down)")
