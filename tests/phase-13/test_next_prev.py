"""Gate: next/prev changes track (fake 3-track playlist)."""
from conftest import music


def test_next_prev(fake_player):
    fake_player.reset(status="Playing", index=0)
    assert fake_player.track == "track-a"

    r = music("next")
    assert r.code == 200, r.detail
    assert fake_player.track == "track-b", f"truth {fake_player.track}, detail {r.detail!r}"
    assert "track-b" in r.detail, r.detail

    r = music("next")
    assert r.code == 200, r.detail
    assert fake_player.track == "track-c", f"truth {fake_player.track}, detail {r.detail!r}"

    r = music("prev")
    assert r.code == 200, r.detail
    assert fake_player.track == "track-b", f"truth {fake_player.track}, detail {r.detail!r}"
    assert "track-b" in r.detail, r.detail

    r = music("prev")
    assert r.code == 200, r.detail
    assert fake_player.track == "track-a", f"truth {fake_player.track}, detail {r.detail!r}"
