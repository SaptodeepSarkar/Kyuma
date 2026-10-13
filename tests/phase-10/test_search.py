"""Gate: query -> results page URL contains query."""
import os

import pytest

from executor.browser import build_search_url, handle_web_search


def test_build_search_url():
    q = f"kyuma probe {os.getpid()}"
    for engine in ("google", "bing", "duckduckgo", "ddg", "brave"):
        url = build_search_url(q, engine)
        assert "kyuma+probe" in url, (engine, url)
    assert "kyuma+probe" in build_search_url(q), "default engine must embed query"
    with pytest.raises(ValueError):
        build_search_url(q, "yahoo")
    for bad in ("", "  ", None):
        with pytest.raises(ValueError):
            build_search_url(bad)


def test_web_search_live(live_state):
    from conftest import hyprctl
    import json

    q = f"kyuma probe {os.getpid()}"
    r = handle_web_search({"query": q})
    assert r.code == 200, r.detail
    assert "kyuma+probe" in r.detail, f"results URL must contain query: {r.detail}"
    active = json.loads(hyprctl("activewindow", "-j"))
    assert active.get("class") == os.environ.get("KYUMA_BROWSER_CLASS", "zen")
    assert handle_web_search({"query": ""}).code == "error"
    assert handle_web_search({"query": q, "engine": "yahoo"}).code == "error"
