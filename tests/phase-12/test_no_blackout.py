"""Gate: plain set 0 rejected (or clamped), brightness unchanged and nonzero."""
from executor.brightness import handle_brightness_get, handle_brightness_set


def test_no_blackout(backlight):
    r = handle_brightness_set({"value": 50})
    assert r.code == 200, r.detail
    r = handle_brightness_set({"value": 0})
    assert r.code == "error", r.detail
    after = handle_brightness_get({})
    assert after.code == 200, after.detail
    pct = int(after.detail.split()[1].rstrip("%"))
    assert pct > 0, after.detail
    assert after.detail == "brightness 50%", after.detail
