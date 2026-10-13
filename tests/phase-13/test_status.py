"""Gate: state query matches player truth after each op."""
from conftest import music


def _assert_matches(fake_player):
    r = music("status")
    assert r.code == 200, r.detail
    assert fake_player.status in r.detail, f"truth {fake_player.status}, detail {r.detail!r}"
    assert fake_player.track in r.detail, f"truth {fake_player.track}, detail {r.detail!r}"


def test_status(fake_player):
    fake_player.reset(status="Paused", index=0)
    _assert_matches(fake_player)

    assert music("play").code == 200
    _assert_matches(fake_player)

    assert music("next").code == 200
    _assert_matches(fake_player)

    assert music("pause").code == 200
    _assert_matches(fake_player)

    assert music("toggle").code == 200
    _assert_matches(fake_player)

    assert music("prev").code == 200
    _assert_matches(fake_player)
