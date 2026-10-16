# AGENTS.md — Kyuma

AI-powered realtime voice interface for Hyprland. Speak continuously; Kyuma acts mid-speech on short desktop tasks. No multi-step reasoning, no coding, no research.

Source of truth: Obsidian vault `Projects/Kyuma/` (`README.md`, `PRD/`, `Flows/`). If this file conflicts with the vault, ask the user — vault wins until reconciled.

## What it is

- Voice → STT stream → Kyuma harness (moderator) → decision model (Jev or Laya, undecided) → Implementation Harness executes on Hyprland/apps.
- Scope is ONLY small fast tasks: switch workspace, focus window/app/tab, open app/website/search results, volume, brightness, music control. Anything bigger is out of scope — reject, don't extend.
- Sibling project Vaani (`Projects/Vaani/`) is dictation + text formatting, NOT voice control. Don't mix them.

## Repo layout (target)

- `stt/` — streaming ASR (Vosk Indian model default, swappable; needs ~1 RTF).
- `harness/` — moderator: buffer partial words, decide sentence completeness, call model API, forward exec code, flush buffer on 200 or error.
- `executor/` — Implementation Harness: app/website open + focus, search, volume, brightness, music.
- `model-server/` — Laya model manager: load to correct GPU, keep resident, context mgmt, API interface, offloading.
- `ui/` — QuickShell overlay; harness itself runs as a terminal app that spawns services.
- `docs/` — transcribed vault specs and flows (start here before coding).

## Rules

- Realtime first: never block speech on action. STT streams, harness decides mid-utterance, buffer flushes after every dispatch (success or error).
- Keep STT modular — no hardcoded Vosk-only paths; model must be swappable.
- Model server owns GPU placement and residency; harness only calls its API.
- No new top-level services without updating `docs/architecture.md` and vault `Projects/Kyuma/Flows/Working flow.canvas`.
- Empty repo: check `docs/` + vault before scaffolding anything.
- Audio pitfall (2026-10-13): repeated `pw-record` mic capture flips Bluetooth headsets into HSP/HFP calling mode (low quality). Never leave mic capture running; restore A2DP with `pactl set-card-profile <bt-card> a2dp-sink` if it happens.
- STT model rule (2026-10-16): default stays `models/vosk-model-small-en-in-0.4` (Indian English). Bigger `vosk-model-en-us-0.22-lgraph` (205MB) is installed and selectable via `KYUMA_STT_MODEL` — but it hallucinates a word on pure silence (fails phase-03 `test_silence_empty`), so it is NOT the default. Model size was measured to be second-order: the small model transcribes clean audio correctly, so bad transcription means bad input audio, not a weak model.
- Mic rule: default input is `CleanMic` (native PipeWire RNNoise chain, `stt/pipewire/`; suspends at idle, zero extra processes). Falls back to `alsa_input` auto-pick. `KYUMA_MIC_TARGET` overrides. Never capture `bluez_input` (forces HSP music-kill) unless the user explicitly asks.
- UI: QML overlay (`quickshell -p ui/shell.qml`) spawns with `start` by default per user decision (indicator is required); `--no-ui` skips it. If Caelestia freezes, suspect the second QS instance first. Hyprland toasts (`harness/notifier.py`) fire regardless as backup.
