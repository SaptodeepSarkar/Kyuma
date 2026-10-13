# Phase 13 — music

GOAL: Media play/pause/next/prev on the active player.

BUILD: `music {play|pause|toggle|next|prev}` via MPRIS (playerctl — document choice).
No player → error `Result`, not a crash.

GATE (`tests/phase-13/`, require MPRIS player; else skip with reason):
- `test_toggle.py` — toggle flips play/pause state both ways.
- `test_next_prev.py` — next/prev changes track (use a test playlist/fake player).
- `test_no_player.py` — no player running → error `Result`, exit 0.
- `test_status.py` — state query matches player truth after each op.

BACKEND: pure-Python MPRIS over D-Bus via `dbus-next` (shared `.venv`) — no
playerctl binary on this box, no sudo assumed. jeepney rejected (no easy
service export for the fake player).

GATE 2026-10-13: `./tests/gate.sh 13` → 5 passed, 1 skipped. Fake-player tests
GREEN vs `org.mpris.MediaPlayer2.KyumaTest`; `test_no_player_autodetect` skips
with reason (real Spotify on this bus) while the pinned-absent-player test
asserts the error `Result` deterministically. Gate fails pre-phase
(`executor/music.py` did not exist).
