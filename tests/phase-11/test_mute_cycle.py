"""Gate: mute → muted; unmute → restores prior level."""
from conftest import parse_volume, wpctl

from executor.volume import handle_volume

SINK = "@DEFAULT_AUDIO_SINK@"


def test_mute_cycle(audio_state):
    r = handle_volume({"op": "set", "level": 42})
    assert r.code == 200, r.detail
    r = handle_volume({"op": "unmute"})
    assert r.code == 200, r.detail

    r = handle_volume({"op": "mute"})
    assert r.code == 200, r.detail
    _, muted = parse_volume(wpctl("get-volume", SINK))
    assert muted, "mixer not muted after mute"

    r = handle_volume({"op": "unmute"})
    assert r.code == 200, r.detail
    level, muted = parse_volume(wpctl("get-volume", SINK))
    assert not muted, "mixer still muted after unmute"
    assert level == 42, f"prior level not restored: got {level}, want 42"
