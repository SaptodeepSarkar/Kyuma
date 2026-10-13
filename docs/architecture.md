# Architecture

## Pipeline

```
mic → VAD → STT (streaming words) → Kyuma harness (buffer + completeness check)
  → Laya model API (via Model Manager) → exec code → Implementation Harness → Hyprland/apps
  → 200/error → flush buffer → keep listening
```

Speech never blocks on action. The buffer flushes after every dispatch, success or error.

## Pieces

| Piece | Role | Vault spec |
|---|---|---|
| STT System | Word-stream ASR, ~1 RTF, Vosk Indian default, modular | `docs/components/stt-system.md` |
| Kyuma harness | Moderator: buffers fragments, decides completeness, calls model, forwards exec | `docs/components/kyuma-harness.md` |
| Implementation Harness | 8 desktop capabilities (open/focus app+site, search, volume, brightness, music) | `docs/components/implementation-harness.md` |
| Model Manager (Lava/Laya) | Keeps model resident, GPU placement, context, API, offloading | `docs/components/model-manager.md` |
| UI | Terminal app core; QuickShell overlay for status | see harness doc |

Per `Working flow.canvas`: Model Manager exposes the Laya interface; the harness consumes it;
the harness drives the Implementation Harness.

## Boundaries

- Harness never touches Hyprland directly — only via Implementation Harness.
- Model Manager never parses speech — only serves the decision model API.
- STT never decides — only emits words (or nothing on silence).
- Kyuma ≠ Vaani: Vaani is dictation/formatting on SUPER+H; no shared code assumed.

## Phase 01 decision (2026-10-13)

Language + IPC: Python + local HTTP/JSON. Contracts module: `harness/contracts.py`
(`Word{w:text, t:float}`, `Exec{action:str, args:dict}` with 8 closed actions,
`Result{code:200|error, detail:str}`); all JSON-serializable for the HTTP wire.
