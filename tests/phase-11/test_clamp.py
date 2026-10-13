"""Gate: set 150 → error Result, volume unchanged."""
from conftest import parse_volume, wpctl

from executor.volume import handle_volume

SINK = "@DEFAULT_AUDIO_SINK@"


def test_clamp(audio_state):
    before = parse_volume(wpctl("get-volume", SINK))
    r = handle_volume({"op": "set", "level": 150})
    assert r.code == "error", r.detail
    after = parse_volume(wpctl("get-volume", SINK))
    assert after[0] == before[0], f"volume moved {before[0]} -> {after[0]} on rejected set"
