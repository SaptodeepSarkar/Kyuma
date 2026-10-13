"""Gate: open twice -> single instance, focused, no duplicate window."""
from conftest import addrs, close_addr

from executor.apps import handle_open_app


def test_open_focuses_existing(live_state):
    before = addrs()
    try:
        r1 = handle_open_app({"name": "foot"})
        assert r1.code == 200, r1.detail
        mid = addrs()
        r2 = handle_open_app({"name": "foot"})
        assert r2.code == 200, r2.detail
        assert addrs() == mid, "second open_app spawned a duplicate window"
    finally:
        for addr in addrs() - before:
            close_addr(addr)
