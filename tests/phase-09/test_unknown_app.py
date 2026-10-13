"""Gate: unknown app name -> error Result, nothing launched."""
from conftest import addrs

from executor.apps import handle_open_app


def test_unknown_app(live_state):
    before = addrs()
    r = handle_open_app({"name": "__kyuma_no_such_app__"})
    assert r.code == "error", f"expected error Result, got {r!r}"
    assert "unknown app" in r.detail, f"error should say unknown app: {r.detail!r}"
    assert addrs() == before, "unknown app launch created a window"
