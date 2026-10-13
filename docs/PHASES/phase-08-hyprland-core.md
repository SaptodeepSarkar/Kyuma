# Phase 08 — hyprland-core

GOAL: Real workspace switching + window focusing on Hyprland.

BUILD: hyprctl-backed handlers: `switch_workspace {n|name}`, `focus_window {class|title}`.
Resolve names via `hyprctl clients/workspaces -j`. No-op with error `Result` when target
missing (never focus the wrong window).

GATE (`tests/phase-08/`, require Hyprland; else skip with reason):
- `test_switch_workspace.py` — switch away and back → active workspace matches.
- `test_focus_window.py` — open two windows → focus each by class → active client matches.
- `test_missing_target.py` — focus nonexistent class → error `Result`, focus unchanged.
- `test_no_misfocus.py` — ambiguous title → error, not a guess.
