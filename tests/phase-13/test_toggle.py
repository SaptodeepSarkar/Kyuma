"""Gate: toggle flips play/pause state both ways (vs fake player truth)."""
from conftest import music

from executor.dispatch import dispatch


def test_toggle(fake_player):
    fake_player.reset(status="Paused")
    r = music("toggle")
    assert r.code == 200, r.detail
    assert fake_player.status == "Playing", f"truth {fake_player.status}, detail {r.detail!r}"
    assert "Playing" in r.detail, r.detail

    r = music("toggle")
    assert r.code == 200, r.detail
    assert fake_player.status == "Paused", f"truth {fake_player.status}, detail {r.detail!r}"
    assert "Paused" in r.detail, r.detail


def test_toggle_via_dispatch(fake_player):
    """The registered `music` route answers dispatch (router untouched)."""
    from conftest import BUS_NAME

    fake_player.reset(status="Playing")
    r = dispatch({"action": "music", "args": {"op": "toggle", "player": BUS_NAME}})
    assert r.code == 200, r.detail
    assert fake_player.status == "Paused", f"truth {fake_player.status}, detail {r.detail!r}"
