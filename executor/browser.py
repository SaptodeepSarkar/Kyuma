"""Browser control — Phase 10. Import path: ``executor.browser``.

Mechanism (FoxMCP tab automation is UNAVAILABLE, and Hyprland exposes no
tab URLs — ``hyprctl clients`` shows one entry per *window* whose title is
the active tab's title):
- open: ``<browser> --new-tab|--new-window <url>`` (remote into the running
  instance), then focus the newest browser window via Hyprland Lua dispatch.
- focus tab: match hyprctl client titles, exact-first, window granularity.
  Zero or ambiguous matches → error Result, focus untouched.
- search: build the engine results URL, open it as a new tab.

Importing this module registers all three handlers (``dispatch.py`` untouched):
``open_website`` -> handle_open_website, ``focus_website`` -> handle_focus_tab,
``web_search`` -> handle_web_search.

Config (env, read per call so tests can monkeypatch):
- ``KYUMA_BROWSER``: browser binary (default ``zen-browser``; falls back to
  ``xdg-open`` when the binary is missing).
- ``KYUMA_BROWSER_CLASS``: Hyprland window class (default ``zen``).
- ``KYUMA_HOST_ALLOWLIST``: optional comma-separated hosts; when set,
  http(s) URLs outside it are refused (file:// URLs are always local).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import urllib.parse
from typing import Any

from executor import hyprland
from executor.dispatch import register_handler
from harness.contracts import Result

ENGINES = {
    "google": "https://www.google.com/search?q={q}",
    "bing": "https://www.bing.com/search?q={q}",
    "duckduckgo": "https://duckduckgo.com/?q={q}",
    "ddg": "https://duckduckgo.com/?q={q}",
    "brave": "https://search.brave.com/search?q={q}",
}

_SCHEMES = ("http://", "https://", "file://")


def _browser_cmd() -> list[str]:
    """Binary to launch URLs: KYUMA_BROWSER or xdg-open fallback. Raises on none."""
    name = os.environ.get("KYUMA_BROWSER", "zen-browser")
    if shutil.which(name):
        return [name]
    if shutil.which("xdg-open"):
        return ["xdg-open"]
    raise RuntimeError(f"no browser installed (tried {name!r}, xdg-open)")


def _normalize_url(url: Any) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("open_website needs {url}")
    url = url.strip()
    if not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", url):
        url = "https://" + url
    if not url.startswith(_SCHEMES):
        raise ValueError(f"unsupported URL scheme: {url!r}")
    return url


def _check_allowlist(url: str) -> None:
    raw = os.environ.get("KYUMA_HOST_ALLOWLIST", "").strip()
    if not raw or url.startswith("file://"):
        return
    host = urllib.parse.urlparse(url).hostname or ""
    allowed = {h.strip().lower().lstrip(".") for h in raw.split(",") if h.strip()}
    if not any(host.lower() == a or host.lower().endswith("." + a) for a in allowed):
        raise ValueError(f"host {host!r} not in allowlist")


def _wait_for(pred, timeout: float = 10.0):
    deadline = time.monotonic() + timeout
    while True:
        got = pred()
        if got is not None:
            return got
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.25)


def _browser_windows() -> list[dict[str, Any]]:
    try:
        clients = hyprland._json("clients")
    except RuntimeError:
        return []
    cls = os.environ.get("KYUMA_BROWSER_CLASS", "zen")
    return [c for c in clients if c.get("class") == cls]


def _open(url: str, new_window: bool = False) -> Result:
    """Launch url in the browser, focus the newest browser window. Never raises."""
    try:
        cmd = _browser_cmd()
    except RuntimeError as e:
        return Result(code="error", detail=str(e))
    flag = "--new-window" if new_window else "--new-tab"
    try:
        subprocess.Popen(
            [*cmd, flag, url] if cmd != ["xdg-open"] else [*cmd, url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as e:
        return Result(code="error", detail=f"browser launch failed: {e}")
    wins = _wait_for(lambda: _browser_windows() or None)
    if not wins:
        return Result(code="error", detail="browser window did not appear")
    target = max(wins, key=lambda c: c.get("focusHistoryID", 0))
    addr = target.get("address")
    try:
        hyprland._hyprctl("dispatch", f'hl.dsp.focus({{ window = "address:{addr}" }})')
        active = hyprland._json("activewindow")
    except RuntimeError as e:
        return Result(code="error", detail=str(e))
    if str(active.get("address")) != str(addr):
        return Result(code="error", detail="browser focus did not stick")
    return Result(code=200, detail=f"opened {url}")


def handle_open_website(args: dict[str, Any]) -> Result:
    """Open a URL in a browser tab. ``args``: {"url": str, "new_window"?: bool}."""
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    try:
        url = _normalize_url(args.get("url"))
        _check_allowlist(url)
    except ValueError as e:
        return Result(code="error", detail=str(e))
    return _open(url, new_window=bool(args.get("new_window", False)))


def _base_title(title: str) -> str:
    """Window title minus the trailing ' — <app>' suffix, e.g. Zen appends its name."""
    head, _, _ = str(title).rpartition(" — ")
    return head or str(title)


def handle_focus_tab(args: dict[str, Any]) -> Result:
    """Focus the browser window whose tab title matches. ``args``: {"query": str}.

    Exact title match (minus app suffix) wins; else one case-insensitive
    substring hit. Zero or ambiguous matches → error, focus untouched.
    """
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return Result(code="error", detail="focus_tab needs {query}")
    wins = _browser_windows()
    if not wins:
        return Result(code="error", detail="no browser window found")
    needle = query.strip().casefold()
    exact = [
        w
        for w in wins
        if needle in (_base_title(w.get("title", "")).casefold(), str(w.get("title", "")).casefold())
    ]
    if len(exact) == 1:
        matches = exact
    elif exact:
        matches = exact  # several exact hits are still ambiguous
    else:
        matches = [w for w in wins if needle in str(w.get("title", "")).casefold()]
    if not matches:
        return Result(code="error", detail=f"no tab matches {query!r}")
    if len(matches) > 1:
        addrs = [m.get("address") for m in matches]
        return Result(
            code="error",
            detail=f"ambiguous: {len(matches)} tabs match {query!r} {addrs}, refusing to guess",
        )
    addr = matches[0].get("address")
    try:
        hyprland._hyprctl("dispatch", f'hl.dsp.focus({{ window = "address:{addr}" }})')
        active = hyprland._json("activewindow")
    except RuntimeError as e:
        return Result(code="error", detail=str(e))
    if str(active.get("address")) != str(addr):
        return Result(code="error", detail=f"focus on tab {query!r} did not stick")
    return Result(code=200, detail=f"focused tab {matches[0].get('title')}")


def build_search_url(query: str, engine: str = "google") -> str:
    """Pure helper: results-page URL for query. Raises ValueError on bad input."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("web_search needs {query}")
    key = str(engine or "google").strip().lower()
    if key not in ENGINES:
        raise ValueError(f"unknown engine {engine!r}, want one of {sorted(ENGINES)}")
    return ENGINES[key].format(q=urllib.parse.quote_plus(query.strip()))


def handle_web_search(args: dict[str, Any]) -> Result:
    """Open engine results page. ``args``: {"query": str, "engine"?: str}."""
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    try:
        url = build_search_url(args.get("query"), args.get("engine", "google"))
    except ValueError as e:
        return Result(code="error", detail=str(e))
    res = _open(url)
    if res.code != 200:
        return res
    return Result(code=200, detail=f"search {args.get('engine', 'google')}: {url}")


register_handler("open_website", handle_open_website)
register_handler("focus_website", handle_focus_tab)
register_handler("web_search", handle_web_search)
