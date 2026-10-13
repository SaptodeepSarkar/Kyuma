"""Gate: background single-instance app -> foreground after focus_app."""
import json

import pytest
from conftest import clients, hyprctl

from executor.apps import handle_focus_app


def test_focus_app(live_state):
    active_addr = json.loads(hyprctl("activewindow", "-j")).get("address")
    counts = {}
    for c in clients():
        counts[c.get("class")] = counts.get(c.get("class"), 0) + 1
    bg = [c for c in clients() if counts[c.get("class")] == 1 and c.get("address") != active_addr]
    if not bg:
        pytest.skip("need a background single-instance window for the focus test")
    want = bg[0]
    r = handle_focus_app({"class": want["class"]})
    assert r.code == 200, r.detail
    active = json.loads(hyprctl("activewindow", "-j"))
    assert active.get("address") == want["address"], (
        f"wanted {want['class']}@{want['address']}, active is "
        f"{active.get('class')}@{active.get('address')}"
    )
