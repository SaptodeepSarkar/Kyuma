# Implementation Harness

Executes decisions on Hyprland and apps. Receives exec code from the Kyuma harness,
returns 200 or error.

Capabilities (closed list — anything else is out of scope):

1. Open application.
2. Open websites.
3. Focus already-opened websites.
4. Focus already-opened applications.
5. Open search results in the browser.
6. Control volume.
7. Control brightness.
8. Control music.
9. Switch workspace (`switch_workspace`).
10. Focus window (`focus_window`).

Action names are the frozen `harness.contracts.ACTIONS` list: `open_app`,
`open_website`, `focus_website`, `focus_app`, `web_search`, `volume`,
`brightness`, `music`, `switch_workspace`, `focus_window`. Anything else
(close/kill/quit, raw shell) is out of scope — the dispatcher rejects it.

Wiring note (2026-10-13, Phase 16 audit, corrected after Phase 14 landed):
production wiring is `executor.register_all()` (binds volume, brightness,
switch_workspace/focus_window, music when present; apps+browser self-register),
called by `harness.loop` — the only production consumer. `import executor`
alone stays side-effect free so gate 07's stub assertions hold.

Arg-key note: the decision prompt emits brightness-set as
`{"op": "set", "level": N}`, but `handle_brightness_set` reads
`args["value"]` (+ `force: true` for 0). A model-shaped brightness-set is
currently rejected by the handler — prompt/handler key alignment is owed
by the decision owner. Volume uses `level` on both sides (aligned).
