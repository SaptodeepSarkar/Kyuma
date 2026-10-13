"""Gate: set 50% → reads back 50%."""
from executor.brightness import handle_brightness_get, handle_brightness_set


def test_set(backlight):
    r = handle_brightness_set({"value": 50})
    assert r.code == 200, r.detail
    r = handle_brightness_get({})
    assert r.code == 200, r.detail
    assert r.detail == "brightness 50%", r.detail
