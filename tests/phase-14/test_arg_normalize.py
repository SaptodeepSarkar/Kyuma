"""Prompt arg keys normalize to handler arg keys (Phase 16 integration fix)."""
from harness.loop import normalize


def test_aliases():
    assert normalize("open_app", {"app": "firefox"}) == {"name": "firefox"}
    assert normalize("focus_app", {"app": "discord"}) == {"class": "discord"}
    assert normalize("open_website", {"site": "youtube"}) == {"url": "youtube"}
    assert normalize("focus_website", {"site": "yt"}) == {"query": "yt"}
    assert normalize("switch_workspace", {"workspace": "3"}) == {"n": "3"}
    assert normalize("focus_window", {"window": "dl"}) == {"title": "dl"}
    assert normalize("brightness", {"op": "set", "level": 70}) == {"op": "set", "value": 70}
    # passthrough + no-mutate
    assert normalize("volume", {"op": "up"}) == {"op": "up"}
    assert normalize("volume", {"command": "up"}) == {"op": "up"}
    assert normalize("music", {"command": "next"}) == {"op": "next"}
    assert normalize("music", {"op": "next"}) == {"op": "next"}
    src = {"app": "x"}
    normalize("open_app", src)
    assert src == {"app": "x"}
