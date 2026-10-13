"""Gate: two tabs -> focus by keyword lands on the right one."""
import os

from conftest import active_address, kill_window, make_page, wait_title

from executor.browser import handle_focus_tab, handle_open_website


def test_focus_tab(live_state):
    tag = os.getpid()
    url_a = make_page("tabA", f"KyumaTabA-{tag}")
    url_b = make_page("tabB", f"KyumaTabB-{tag}")
    addrs = []
    try:
        assert handle_open_website({"url": url_a, "new_window": True}).code == 200
        assert handle_open_website({"url": url_b, "new_window": True}).code == 200
        win_a = wait_title(f"KyumaTabA-{tag}")
        win_b = wait_title(f"KyumaTabB-{tag}")
        assert win_a and win_b, "both tabs must exist"
        assert win_a["address"] != win_b["address"], "tabs need separate windows"
        addrs = [win_a["address"], win_b["address"]]

        r = handle_focus_tab({"query": f"KyumaTabA-{tag}"})
        assert r.code == 200, r.detail
        assert active_address() == str(win_a["address"])

        r = handle_focus_tab({"query": "kytaba"})  # junk, case differs anyway
        assert r.code == "error"

        r = handle_focus_tab({"query": f"kyumatabb-{tag}"})  # substring, lowercase
        assert r.code == 200, r.detail
        assert active_address() == str(win_b["address"])
    finally:
        for a in addrs:
            kill_window(a)
