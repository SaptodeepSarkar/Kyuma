"""Gate: focus nonexistent class → error Result, focus unchanged."""
import json

from conftest import hyprctl

from executor.hyprland import handle_focus_window


def test_missing_target(live_state):
    before = json.loads(hyprctl("activewindow", "-j")).get("address")
    r = handle_focus_window({"class": "__kyuma_no_such_class__"})
    assert r.code == "error", f"expected error Result, got {r!r}"
    after = json.loads(hyprctl("activewindow", "-j")).get("address")
    assert after == before, f"focus moved on missing target: {before} -> {after}"
