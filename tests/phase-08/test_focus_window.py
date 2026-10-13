"""Gate: focus two distinct-class windows by class → active client matches."""
import json

from conftest import hyprctl

from executor.hyprland import handle_focus_window


def test_focus_window(live_state):
    import pytest

    clients = json.loads(hyprctl("clients", "-j"))
    by_class = {}
    counts = {}
    for c in clients:
        counts[c.get("class")] = counts.get(c.get("class"), 0) + 1
        by_class.setdefault(c.get("class"), c)
    singles = [c for c in by_class.values() if counts[c.get("class")] == 1]
    if len(singles) < 2:
        pytest.skip(f"need ≥2 unambiguous window classes, have {counts}")
    targets = singles[:2]

    for want in targets:
        r = handle_focus_window({"class": want["class"]})
        assert r.code == 200, r.detail
        active = json.loads(hyprctl("activewindow", "-j"))
        assert active.get("address") == want["address"], (
            f"wanted {want['class']}@{want['address']}, active is "
            f"{active.get('class')}@{active.get('address')}"
        )
