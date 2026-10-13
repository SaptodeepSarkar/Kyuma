"""Phase 11 — volume control via wpctl. Import path: ``executor.volume``.

Choice: ``wpctl`` (not ``pactl``) — native PipeWire/WirePlumber CLI on this
Arch box, already present, sink addressing via ``@DEFAULT_AUDIO_SINK@``
(no ID lookup needed). ``pactl`` would go through the Pulse compat layer.

Real ``wpctl`` calls happen only inside the handler (never at import time).
``handle_volume`` takes an args dict ``{"op": ..., "level": ...}`` and returns
``harness.contracts.Result``. Mute is a separate PipeWire flag, so the mixer
itself preserves the level across mute/unmute — unmute restores prior level
with no bookkeeping here.

Ops: get | set (needs level 0-100) | up | down (STEP) | mute | unmute.
``set`` outside 0-100 → error Result, mixer untouched. ``up`` is capped at
100% via ``wpctl -l 1.0``.
"""
from __future__ import annotations

import re
import subprocess
from typing import Any

from harness.contracts import Result

SINK = "@DEFAULT_AUDIO_SINK@"

#: up/down step in percentage points (asserted by test_up_down.py).
STEP = 5

_VOL_RE = re.compile(r"Volume:\s+([0-9.]+)")


def _wpctl(*args: str) -> str:
    """Run ``wpctl`` and return stdout; raise RuntimeError on failure."""
    try:
        proc = subprocess.run(
            ["wpctl", *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"wpctl not runnable: {e}") from e
    if proc.returncode != 0:
        raise RuntimeError(f"wpctl {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _read() -> tuple[int, bool]:
    """Return (percent 0+, muted). Percent may exceed 100 on a loud sink."""
    out = _wpctl("get-volume", SINK)
    m = _VOL_RE.search(out)
    if not m:
        raise RuntimeError(f"unparseable wpctl output: {out.strip()!r}")
    return round(float(m.group(1)) * 100), "[MUTED]" in out


def _describe() -> str:
    level, muted = _read()
    return f"volume {level}%{' (muted)' if muted else ''}"


def handle_volume(args: dict[str, Any]) -> Result:
    """Volume ops. ``args``: {"op": get|set|up|down|mute|unmute, "level": 0-100}."""
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    op = args.get("op", "get")
    if op not in ("get", "set", "up", "down", "mute", "unmute"):
        return Result(code="error", detail=f"unknown volume op: {op!r}")
    try:
        if op == "get":
            return Result(code=200, detail=_describe())
        if op == "set":
            level = args.get("level")
            if isinstance(level, bool) or not isinstance(level, (int, float)):
                return Result(code="error", detail=f"set needs level 0-100, got {level!r}")
            if not 0 <= level <= 100:
                return Result(code="error", detail=f"level {level!r} out of range 0-100, unchanged")
            _wpctl("set-volume", SINK, f"{float(level) / 100:.4f}")
            return Result(code=200, detail=_describe())
        if op in ("up", "down"):
            sign = "+" if op == "up" else "-"
            _wpctl("set-volume", "-l", "1.0", SINK, f"{STEP}%{sign}")
            return Result(code=200, detail=_describe())
        _wpctl("set-mute", SINK, "1" if op == "mute" else "0")
        return Result(code=200, detail=_describe())
    except RuntimeError as e:
        return Result(code="error", detail=str(e))
