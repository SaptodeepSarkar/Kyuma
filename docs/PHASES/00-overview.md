# PHASES — 16 gated build phases

Each phase has GOAL → BUILD → GATE (multiple tests). The next phase does not start until the
goal is met and every gate passes (`tests/gate.sh <NN>` green).

Map: `docs/PHASES/phase-NN-<name>.md` ↔ `tests/phase-NN/`.

| # | Phase | Goal |
|---|---|---|
| 01 | scaffold-contracts | Repo skeleton + frozen message schemas (STT word, exec action, result) |
| 02 | vad-gate | Mic VAD splits speech/silence; silence emits nothing |
| 03 | stt-stream | Vosk streaming words at ~1 RTF, model swappable |
| 04 | buffer-complete | Buffer fragments; fire only on complete command |
| 05 | model-server | Resident model API (load, GPU place, context, offload) |
| 06 | decision-json | Qwen 1.5B maps sentence → valid exec JSON for all 8 intents |
| 07 | exec-dispatch | Dispatcher validates exec JSON, routes to capability, returns 200/error |
| 08 | hyprland-core | Workspace switch + window focus via hyprctl |
| 09 | app-control | Open app + focus opened app |
| 10 | browser-control | Open site, focus tab, open search results |
| 11 | volume | Volume get/set/mute |
| 12 | brightness | Brightness get/set |
| 13 | music | Play/pause/next/prev |
| 14 | loop-flush | Full loop: speech → action → flush on 200 AND error, never blocks speech |
| 15 | supervisor-ui | Terminal supervisor spawns all services + QuickShell status UI |
| 16 | harden-release | Latency budget, soak test, docs + vault sync |
