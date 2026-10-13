# Phase 15 — supervisor-ui

GOAL: One terminal command boots everything; QuickShell shows live status.

BUILD: Supervisor (terminal app) spawns STT, model-server, executor in order, restarts dead
children, shuts down cleanly on SIGINT. QuickShell overlay: listening state, last sentence,
last action + result. Supervisor crash → children reaped, no orphans.

GATE (`tests/phase-15/`):
- `test_boot_order.py` — start → all three services healthy within timeout.
- `test_restart.py` — kill a child → supervisor restarts it, healthy again.
- `test_clean_shutdown.py` — SIGINT → all children exit, no orphan PIDs.
- `test_ui_state.py` — UI shows last sentence + result after a loop run (headless assert on
  the state object if QuickShell can't run in test env).

## Run (Wave 4 implementation)

- Boot: `.venv/bin/python harness/supervisor.py start` (foreground; Ctrl-C stops).
  `stop` / `status` subcommands; `start --ui` also spawns the overlay.
- Overlay: `quickshell -p ui/shell.qml` (path launch is `-p`, not `-c`).
- Loop contract (Phase 14 sibling must conform): entry is `harness/loop.py:main()`;
  the loop MUST write `$KYUMA_STATE_FILE` (default `/tmp/kyuma-state.json`) as
  `{listening, last_sentence, last_action, result, ts}` at startup and on every
  dispatch. Supervisor treats a fresh write (mtime >= loop spawn) as loop-healthy.
- Supervisor manages two children (model-server wrapper + harness loop; STT and
  executor live inside the loop per Phase 14, not as separate processes).
  Restart budget 3 per child, then error exit. Children run in own process
  groups; `stop` also sweeps status-file PIDs so a crashed supervisor leaves no
  orphans. Status file gains `ready: true` once all children are healthy.
- Gate: `./tests/gate.sh 15` — stubs stand in for model/loop via
  `KYUMA_MODEL_CMD` / `KYUMA_LOOP_CMD`; real binaries need no GPU in the gate.
