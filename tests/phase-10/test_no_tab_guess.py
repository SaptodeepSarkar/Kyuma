"""Gate: ambiguous/no-match query -> error Result, active tab unchanged."""
import os

from conftest import active_address, kill_window, make_page, wait_title

from executor.browser import handle_focus_tab, handle_open_website


def test_no_match_leaves_focus(live_state):
    before = active_address()
    r = handle_focus_tab({"query": f"zzz-no-such-tab-{os.getpid()}"})
    assert r.code == "error", r.detail
    assert "no tab matches" in r.detail
    assert active_address() == before


def test_ambiguous_leaves_focus(live_state):
    tag = os.getpid()
    addrs = []
    try:
        assert (
            handle_open_website(
                {"url": make_page("ambA", f"KyumaShared-{tag}-One"), "new_window": True}
            ).code
            == 200
        )
        assert (
            handle_open_website(
                {"url": make_page("ambB", f"KyumaShared-{tag}-Two"), "new_window": True}
            ).code
            == 200
        )
        win_a = wait_title(f"KyumaShared-{tag}-One")
        win_b = wait_title(f"KyumaShared-{tag}-Two")
        assert win_a and win_b, "both tabs must exist"
        addrs = [win_a["address"], win_b["address"]]
        before = active_address()
        r = handle_focus_tab({"query": f"KyumaShared-{tag}"})
        assert r.code == "error", r.detail
        assert "ambiguous" in r.detail
        assert active_address() == before, "ambiguous query must not move focus"
    finally:
        for a in addrs:
            kill_window(a)


def test_focus_tab_bad_args(live_state):
    before = active_address()
    for bad in ({}, {"query": ""}, {"query": "  "}, {"query": None}, "nope"):
        assert handle_focus_tab(bad).code == "error", bad
    assert active_address() == before
