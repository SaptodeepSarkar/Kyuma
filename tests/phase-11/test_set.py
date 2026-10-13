"""Gate: set 42 → mixer reads 42."""
from conftest import parse_volume, wpctl

from executor.volume import handle_volume

SINK = "@DEFAULT_AUDIO_SINK@"


def test_set(audio_state):
    r = handle_volume({"op": "set", "level": 42})
    assert r.code == 200, r.detail
    level, _ = parse_volume(wpctl("get-volume", SINK))
    assert level == 42, f"mixer reads {level}, want 42"
