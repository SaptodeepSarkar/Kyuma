"""Phase 08 shared fixture: require live Hyprland, snapshot + restore session state."""
import json
import subprocess

import pytest


def hyprctl(*args):
    proc = subprocess.run(["hyprctl", *args], capture_output=True, text=True, timeout=10)
    if proc.returncode != 0:
        raise RuntimeError(f"hyprctl {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


@pytest.fixture
def live_state():
    """Skip when Hyprland is unreachable; else snapshot ws/focus, restore after."""
    try:
        ws = json.loads(hyprctl("activeworkspace", "-j"))
        try:
            win = json.loads(hyprctl("activewindow", "-j"))
        except RuntimeError:
            win = {}
    except (RuntimeError, OSError, json.JSONDecodeError) as e:
        pytest.skip(f"Hyprland required: {e}")
    saved = {"workspace_id": ws.get("id"), "window_addr": (win or {}).get("address")}
    yield saved
    # Restore: re-focus original window (also returns to its workspace),
    # then ensure original workspace is active. Best-effort, never fails tests.
    try:
        if saved["window_addr"]:
            hyprctl("dispatch", f'hl.dsp.focus({{ window = "address:{saved["window_addr"]}" }})')
        hyprctl("dispatch", f'hl.dsp.focus({{ workspace = "{saved["workspace_id"]}" }})')
    except Exception as e:  # noqa: BLE001 — restore must not fail the gate
        print(f"\nWARNING: session restore failed: {e}")
