"""Gate: up/down moves by the documented step (STEP_PCT)."""
from executor.brightness import (
    STEP_PCT,
    handle_brightness_down,
    handle_brightness_get,
    handle_brightness_set,
    handle_brightness_up,
)


def test_up_down(backlight):
    r = handle_brightness_set({"value": 50})
    assert r.code == 200, r.detail
    r = handle_brightness_up({})
    assert r.code == 200, r.detail
    assert r.detail == f"brightness {50 + STEP_PCT}%", r.detail
    r = handle_brightness_down({})
    assert r.code == 200, r.detail
    assert r.detail == "brightness 50%", r.detail
    # get agrees with the last mutation
    assert handle_brightness_get({}).detail == "brightness 50%"
