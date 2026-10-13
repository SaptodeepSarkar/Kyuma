# Phase 09 — app-control

GOAL: Open any app; focus it if already open.

BUILD: `open_app {name}` (desktop-file lookup + launch), `focus_app {class}` (reuse Phase 08).
"Open" when already running → focus instead (no duplicate instance).

GATE (`tests/phase-09/`, require Hyprland; else skip with reason):
- `test_open_app.py` — open a known app → client appears.
- `test_open_focuses_existing.py` — open twice → single instance, focused.
- `test_unknown_app.py` — unknown name → error `Result`, nothing launched.
- `test_focus_app.py` — background app → foreground after focus.

STATUS: built 2026-10-13 (`executor/apps.py`: desktop-file lookup +
detached launch; already-running → focus, no duplicate; `focus_app`
delegates to Phase 08 `handle_focus_window`). Gate `./tests/gate.sh 09`:
4 passed, no stray windows.
