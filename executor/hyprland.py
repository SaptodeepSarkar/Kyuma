"""Hyprland-backed handlers — Phase 08. Import path: ``executor.hyprland``.

Real ``hyprctl`` calls happen only inside the handlers (never at import
time). Both handlers take an args dict and return ``harness.contracts.Result``.
On any resolution failure they return an error ``Result`` WITHOUT touching
window focus — never focus the wrong window, never guess on ambiguity.

Dispatch uses the Hyprland ≥0.55 Lua syntax, e.g.
``hyprctl dispatch 'hl.dsp.focus({ workspace = "3" })'``.
"""
from __future__ import annotations

import json
import subprocess
from typing import Any

from harness.contracts import Result


def _hyprctl(*args: str) -> str:
    """Run ``hyprctl`` and return stdout; raise RuntimeError on failure."""
    try:
        proc = subprocess.run(
            ["hyprctl", *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"hyprctl not runnable: {e}") from e
    if proc.returncode != 0:
        raise RuntimeError(f"hyprctl {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _json(hyprctl_args: str) -> Any:
    return json.loads(_hyprctl(*hyprctl_args.split(), "-j"))


def handle_switch_workspace(args: dict[str, Any]) -> Result:
    """Switch workspace. ``args``: {"n": int|str} or {"name": str}."""
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    target = args.get("n", args.get("name"))
    if isinstance(target, bool) or target is None or target == "":
        return Result(code="error", detail="switch_workspace needs {n|name}")
    if isinstance(target, int):
        if target < 1:
            return Result(code="error", detail=f"bad workspace id: {target!r}")
        want = str(target)
    elif isinstance(target, str) and target.isdigit():
        want = str(int(target))  # normalize "03" -> "3"
    elif isinstance(target, str):
        try:
            workspaces = _json("workspaces")
        except RuntimeError as e:
            return Result(code="error", detail=str(e))
        names = {str(w.get("name")) for w in workspaces}
        ids = {str(w.get("id")) for w in workspaces}
        if target not in names and target not in ids:
            return Result(code="error", detail=f"unknown workspace: {target!r}")
        want = target
    else:
        return Result(code="error", detail=f"bad workspace target: {target!r}")
    try:
        _hyprctl("dispatch", f'hl.dsp.focus({{ workspace = "{want}" }})')
        active = _json("activeworkspace")
    except RuntimeError as e:
        return Result(code="error", detail=str(e))
    if str(active.get("id")) != want and str(active.get("name")) != want:
        return Result(code="error", detail=f"workspace {want!r} not active after switch")
    return Result(code=200, detail=f"switched to workspace {active.get('name')}")


def handle_focus_window(args: dict[str, Any]) -> Result:
    """Focus one window. ``args``: {"class": str} and/or {"title": str}.

    class matches exactly; title matches case-insensitively as a substring.
    Zero or ambiguous (>1) matches → error Result, focus untouched.
    """
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    cls = args.get("class")
    title = args.get("title")
    if not cls and not title:
        return Result(code="error", detail="focus_window needs {class|title}")
    try:
        clients = _json("clients")
    except RuntimeError as e:
        return Result(code="error", detail=str(e))
    matches = list(clients)
    if cls:
        matches = [c for c in matches if c.get("class") == cls]
    if title:
        needle = str(title).lower()
        matches = [c for c in matches if needle in str(c.get("title", "")).lower()]
    if not matches:
        return Result(code="error", detail=f"no window matches {args!r}")
    if len(matches) > 1:
        addrs = [m.get("address") for m in matches]
        return Result(
            code="error",
            detail=f"ambiguous: {len(matches)} windows match {args!r} {addrs}, refusing to guess",
        )
    addr = matches[0].get("address")
    try:
        _hyprctl("dispatch", f'hl.dsp.focus({{ window = "address:{addr}" }})')
        active = _json("activewindow")
    except RuntimeError as e:
        return Result(code="error", detail=str(e))
    if str(active.get("address")) != str(addr):
        return Result(code="error", detail=f"focus on {addr} did not stick")
    return Result(code=200, detail=f"focused {matches[0].get('class')}:{matches[0].get('title')}")
