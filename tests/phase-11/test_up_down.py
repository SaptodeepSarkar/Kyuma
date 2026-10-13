"""Gate: up/down moves by the documented STEP."""
from conftest import parse_volume, wpctl

from executor.volume import STEP, handle_volume

SINK = "@DEFAULT_AUDIO_SINK@"


def test_up_down(audio_state):
    assert handle_volume({"op": "set", "level": 42}).code == 200
    assert handle_volume({"op": "unmute"}).code == 200

    r = handle_volume({"op": "up"})
    assert r.code == 200, r.detail
    level, _ = parse_volume(wpctl("get-volume", SINK))
    assert level == 42 + STEP, f"up moved to {level}, want {42 + STEP} (STEP={STEP})"

    r = handle_volume({"op": "down"})
    assert r.code == 200, r.detail
    level, _ = parse_volume(wpctl("get-volume", SINK))
    assert level == 42, f"down moved to {level}, want 42"
