"""App open/focus handlers — Phase 09. Import path: ``executor.apps``.

Importing this module registers ``open_app``/``focus_app`` via
``executor.dispatch.register_handler`` (the dispatch router is untouched).

``open_app {name}`` resolves ``name`` against ``*.desktop`` files in
``~/.local/share/applications`` (first, so user entries win) and
``/usr/share/applications``: a hit is a stem, ``Name=``, ``StartupWMClass=``,
or ``Exec`` basename match (all case-insensitive). The ``Exec=`` line is
launched detached (``start_new_session``, no output capture). If a client
with a matching class is already running, it is focused instead — never a
duplicate instance.

``focus_app {class}`` delegates to Phase 08 ``handle_focus_window``.
"""
from __future__ import annotations

import configparser
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

from harness.contracts import Result

from executor.dispatch import register_handler
from executor.hyprland import _hyprctl, _json, handle_focus_window

_APP_DIRS = (
    Path.home() / ".local" / "share" / "applications",
    Path("/usr/share/applications"),
)

_POLL_INTERVAL = 0.25
_POLL_ROUNDS = 24  # ~6 s for the new client to map


def _entry(path: Path) -> dict[str, str]:
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str  # keep key case ("Exec", "Name", ...)
    try:
        cp.read(path, encoding="utf-8")
        return dict(cp["Desktop Entry"])
    except Exception:
        return {}


def _resolve(name: str) -> tuple[list[str], set[str]] | None:
    """Resolve app name -> (exec argv, class candidates). None if unknown."""
    want = name.strip().lower()
    if not want:
        return None
    for appdir in _APP_DIRS:
        if not appdir.is_dir():
            continue
        for fp in sorted(appdir.glob("*.desktop")):
            e = _entry(fp)
            if e.get("Type", "Application") != "Application":
                continue
            cands = {fp.stem.lower()}
            for key in ("Name", "StartupWMClass", "GenericName"):
                if e.get(key):
                    cands.add(e[key].strip().lower())
            exec_line = e.get("Exec", "").strip()
            if exec_line:
                try:
                    argv = [t for t in shlex.split(exec_line) if not t.startswith("%")]
                except ValueError:
                    continue
                if argv:
                    cands.add(Path(argv[0]).name.lower())
            else:
                argv = []
            if want in cands and argv:
                return argv, cands
    return None


def _focus_addr(addr: str) -> bool:
    """Focus a client by address via the Lua-dispatch convention. True if stuck."""
    try:
        _hyprctl("dispatch", f'hl.dsp.focus({{ window = "address:{addr}" }})')
        active = _json("activewindow")
    except RuntimeError:
        return False
    return str((active or {}).get("address")) == str(addr)


def handle_open_app(args: dict[str, Any]) -> Result:
    """Open an app by name; focus it if already running (no duplicates)."""
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    name = args.get("name")
    if not isinstance(name, str) or not name.strip():
        return Result(code="error", detail="open_app needs {name}")
    resolved = _resolve(name)
    if resolved is None:
        return Result(code="error", detail=f"unknown app: {name.strip()!r}")
    argv, cands = resolved
    try:
        clients = _json("clients")
    except RuntimeError as e:
        return Result(code="error", detail=str(e))
    running = [c for c in clients if str(c.get("class", "")).lower() in cands]
    if running:
        addr = running[0].get("address")
        if _focus_addr(addr):
            return Result(code=200, detail=f"{name.strip()} already running, focused")
        return Result(code="error", detail=f"focus on running {name.strip()!r} did not stick")
    before = {c.get("address") for c in clients}
    try:
        subprocess.Popen(  # noqa: S603 — argv comes from installed desktop files
            argv,
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as e:
        return Result(code="error", detail=f"launch {argv[0]!r} failed: {e}")
    new_addr: Any = None
    for _ in range(_POLL_ROUNDS):
        try:
            after = _json("clients")
        except RuntimeError:
            break
        fresh = [
            c
            for c in after
            if c.get("address") not in before
            and str(c.get("class", "")).lower() in cands
        ]
        if fresh:
            new_addr = fresh[0].get("address")
            break
        time.sleep(_POLL_INTERVAL)
    if new_addr is None:
        return Result(code="error", detail=f"launched {argv[0]!r} but no window appeared")
    if not _focus_addr(new_addr):
        # New windows normally map focused; report launch, not focus, as done.
        return Result(code=200, detail=f"opened {name.strip()} (focus did not stick)")
    return Result(code=200, detail=f"opened {name.strip()}")


def handle_focus_app(args: dict[str, Any]) -> Result:
    """Focus a running app by window class (Phase 08 semantics)."""
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    cls = args.get("class")
    if not isinstance(cls, str) or not cls:
        return Result(code="error", detail="focus_app needs {class}")
    return handle_focus_window({"class": cls})


register_handler("open_app", handle_open_app)
register_handler("focus_app", handle_focus_app)
