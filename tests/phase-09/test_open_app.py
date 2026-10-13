"""Gate: open a known app -> 200 Result, its client present and focused."""
import json

from conftest import addrs, clients, close_addr, hyprctl

from executor.apps import handle_open_app


def test_open_app(live_state):
    before = addrs()
    r = handle_open_app({"name": "foot"})
    assert r.code == 200, r.detail
    try:
        foots = [c for c in clients() if str(c.get("class", "")).lower() == "foot"]
        assert foots, "no foot client after open_app"
        active = json.loads(hyprctl("activewindow", "-j"))
        assert str(active.get("class", "")).lower() == "foot", (
            f"foot not focused after open: active is {active.get('class')}"
        )
    finally:
        for addr in addrs() - before:
            close_addr(addr)
