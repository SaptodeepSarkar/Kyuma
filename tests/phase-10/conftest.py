"""Phase 10 shared fixtures: require live Hyprland + installed browser, restore focus."""
import json
import os
import shutil
import subprocess
import time

import pytest

import executor.browser as browser


def hyprctl(*args):
    proc = subprocess.run(["hyprctl", *args], capture_output=True, text=True, timeout=10)
    if proc.returncode != 0:
        raise RuntimeError(f"hyprctl {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


@pytest.fixture
def live_state():
    """Skip without Hyprland/browser; else snapshot focus, restore after."""
    try:
        ws = json.loads(hyprctl("activeworkspace", "-j"))
        try:
            win = json.loads(hyprctl("activewindow", "-j"))
        except RuntimeError:
            win = {}
    except (RuntimeError, OSError, json.JSONDecodeError) as e:
        pytest.skip(f"Hyprland required: {e}")
    if not shutil.which(os.environ.get("KYUMA_BROWSER", "zen-browser")) and not shutil.which(
        "xdg-open"
    ):
        pytest.skip("no browser installed (no KYUMA_BROWSER binary, no xdg-open)")
    saved = {"workspace_id": ws.get("id"), "window_addr": (win or {}).get("address")}
    yield saved
    try:
        if saved["window_addr"]:
            hyprctl("dispatch", f'hl.dsp.focus({{ window = "address:{saved["window_addr"]}" }})')
        hyprctl("dispatch", f'hl.dsp.focus({{ workspace = "{saved["workspace_id"]}" }})')
    except Exception as e:  # noqa: BLE001 — restore must not fail the gate
        print(f"\nWARNING: session restore failed: {e}")


def make_page(name: str, title: str) -> str:
    path = f"/tmp/opencode_kyuma_{name}.html"
    with open(path, "w") as f:
        f.write(f"<html><head><title>{title}</title></head><body>{name}</body></html>")
    return "file://" + path


def wait_title(needle: str, timeout: float = 12.0):
    """Poll zen windows until one title contains needle; return it or None."""
    deadline = time.monotonic() + timeout
    while True:
        for w in browser._browser_windows():
            if needle in str(w.get("title", "")):
                return w
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.3)


def active_address() -> str:
    return str(json.loads(hyprctl("activewindow", "-j")).get("address"))


def kill_window(addr: str) -> None:
    try:
        # Hyprland 0.56 Lua dispatch (plain `killwindow address:` no longer parses).
        hyprctl("dispatch", f'hl.dsp.window.close({{ window = "address:{addr}" }})')
    except RuntimeError as e:
        print(f"\nWARNING: killwindow {addr} failed: {e}")
