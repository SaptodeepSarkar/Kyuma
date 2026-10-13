"""Gate: URL opens in a tab (host allowlist respected if configured)."""
import os

from conftest import active_address, make_page, wait_title

import executor.browser as browser


def test_open_website(live_state):
    marker = f"KyumaOpen-{os.getpid()}"
    url = make_page("open", marker)
    r = browser.handle_open_website({"url": url})
    assert r.code == 200, r.detail
    assert wait_title(marker) is not None, f"tab for {url} never appeared"


def test_open_website_bare_host_gets_scheme(monkeypatch):
    monkeypatch.delenv("KYUMA_HOST_ALLOWLIST", raising=False)
    seen = {}

    def fake_open(url, new_window=False):
        seen["url"] = url
        from harness.contracts import Result

        return Result(code=200, detail=f"opened {url}")

    monkeypatch.setattr(browser, "_open", fake_open)
    r = browser.handle_open_website({"url": "example.com"})
    assert r.code == 200, r.detail
    assert seen["url"] == "https://example.com"


def test_open_website_allowlist(monkeypatch):
    monkeypatch.setenv("KYUMA_HOST_ALLOWLIST", "example.com")
    before = active_address()
    r = browser.handle_open_website({"url": "https://notallowed.test/x"})
    assert r.code == "error", r.detail
    assert "allowlist" in r.detail
    assert active_address() == before, "refused open must not move focus"


def test_open_website_bad_url():
    for bad in ("", "   ", "gopher://x", "javascript:alert(1)", None, 42):
        r = browser.handle_open_website({"url": bad})
        assert r.code == "error", (bad, r.detail)
    assert browser.handle_open_website("not-a-dict").code == "error"
