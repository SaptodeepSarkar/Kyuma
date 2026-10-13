"""Gate: set 200% → error Result, brightness unchanged."""
from executor.brightness import handle_brightness_get, handle_brightness_set


def test_clamp(backlight):
    before = handle_brightness_get({})
    assert before.code == 200, before.detail
    r = handle_brightness_set({"value": 200})
    assert r.code == "error", r.detail
    after = handle_brightness_get({})
    assert after.code == 200, after.detail
    assert after.detail == before.detail, (before.detail, after.detail)
