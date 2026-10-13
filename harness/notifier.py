"""Phase 15b — Hyprland-native status toasts (no second Quickshell instance).

A separate `quickshell -p` overlay can freeze Caelestia, so the default
"Heard you" indicator is `hyprctl notify`, rendered by Hyprland itself:
zero extra processes, zero conflict. Honor KYUMA_NOTIFY=0 to silence.
"""
from __future__ import annotations

import os
import shutil
import subprocess

_enabled: bool | None = None


def enabled() -> bool:
    global _enabled
    if _enabled is None:
        _enabled = os.environ.get("KYUMA_NOTIFY", "1") == "1" and shutil.which("hyprctl") is not None
    return _enabled


def notify(message: str, color: str = "rgb(00ff99)", ms: int = 2500) -> bool:
    """Fire-and-forget toast. Returns False when disabled/unavailable."""
    if not enabled():
        return False
    try:
        subprocess.run(["hyprctl", "notify", "1", str(ms), color, message[:200]],
                       capture_output=True, timeout=5, check=False)
        return True
    except Exception:  # noqa: BLE001 -- indicator must never break the loop
        return False


def heard(sentence: str) -> bool:
    return notify(f"heard: {sentence}", "rgb(00ccff)")


def acted(detail: str, ok: bool = True) -> bool:
    return notify(detail, "rgb(00ff99)" if ok else "rgb(ff5555)")
