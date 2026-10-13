# Phase 10 — browser-control

GOAL: Open sites, focus tabs, run searches — the three browser capabilities.

BUILD: `open_website {url}`, `focus_tab {query}` (match tab title/URL, exact-first), `search {engine?, query}`
(opens results page). Browser target configurable (default: default browser). Uses FoxMCP
tab tools where the harness runs under OpenCode; else browser-remote-debug/file fallback —
document the chosen mechanism.

GATE (`tests/phase-10/`, require browser; else skip with reason):
- `test_open_website.py` — URL opens in a tab (host allowlist respected if configured).
- `test_focus_tab.py` — two tabs → focus by keyword lands on the right one.
- `test_search.py` — query → results page URL contains query.
- `test_no_tab_guess.py` — ambiguous/no-match query → error `Result`, active tab unchanged.

## Mechanism (as built, 2026-10-13)

- Browser found: **Zen Browser** (`/usr/bin/zen-browser`, Hyprland class `zen`,
  already running). FoxMCP tab automation is UNAVAILABLE — no tab APIs exist.
- Open: `<browser> --new-tab|--new-window <url>` (remote into running instance),
  then focus newest browser window via `hl.dsp.focus({window="address:…"})`.
  Binary from `KYUMA_BROWSER` (default `zen-browser`), fallback `xdg-open`;
  class from `KYUMA_BROWSER_CLASS` (default `zen`).
- Focus tab: match `hyprctl clients` titles (window granularity — a window's
  title is its active tab's title; tab URLs are NOT exposed). Exact title
  (minus ` — <app>` suffix) first, else single case-insensitive substring;
  zero/ambiguous → error `Result`, focus untouched.
- Search: `build_search_url()` → engine results URL (google/bing/duckduckgo+ddg/brave,
  `quote_plus`), opened as a new tab. `test_search` asserts the URL embeds the
  query (tab URLs are unreadable via hyprctl, so title assertion is impossible).
- Registration: `executor/browser.py` calls `register_handler()` at import —
  `open_website→handle_open_website`, `focus_website→handle_focus_tab`
  (contract name for "focus tab"), `web_search→handle_web_search`.
  `dispatch.py` untouched. Tests use `file://` probe pages (deterministic,
  offline-proof) + one live Google query.
- Residue: `--new-window` probe windows are closed in teardown via
  `hl.dsp.window.close()` (plain `killwindow address:` no longer parses on
  Hyprland 0.56 Lua dispatch). `--new-tab` probes (open/search tests) leave one
  tab each in the main browser window — single tabs are unclosable via hyprctl.
- Gate: `./tests/gate.sh 10` → 10 passed (Hyprland 0.56.2 live + Zen running;
  skips with reason only when neither is present).
