# Kyuma — AI-powered Hyprland voice interface

Kyuma is a realtime voice-control layer for Hyprland and its applications. A decision-making
model listens via streaming STT and acts on the desktop while the user keeps speaking.

Transcribed from Obsidian vault `Projects/Kyuma/` — vault is source of truth.

## Decision model (researched 2026-10-13, full report in `.research/kyuma-decision-model/`)

**Bake-off done (Phase 06, 2026-10-13): winner Qwen2.5-1.5B-Instruct Q4_K_M**
(96.7% intent accuracy, FAR 0, p95 ~140–250ms on RTX 3050; Qwen3-0.6B eliminated
at 86.7% / 73.3% FAR). Eliminated: Qwen3-0.6B (bake-off),
all Llama-3.2 smalls (BFCL V4 Llama-1B 10.8 vs Qwen3-0.6B 23.9), xLAM-2 (restricted
license), 0.5B-class (too weak), 3B+ (VRAM cost next to Vosk). Why the pair: Qwen leads every
size class on function-calling; GBNF makes JSON validity infrastructure (parse failures ~0 by
construction), so the bake-off tests intent accuracy — 1.5B-class evidence is 92% Top-1 at
~94ms p50 on GPU. Fallback ladder: Qwen2.5-1.5B-Instruct (locked in Phase 06) → sagnik 1.5B-FC finetune
(verify before trusting third-party weights).

## How it works

Streaming STT transcribes speech word-by-word → Kyuma harness buffers fragments until a full
command/sentence forms → decision model picks an action → Implementation Harness executes it.

## What it does (and only this)

Short tasks: switch workspace, focus a window, focus a browser tab, volume, brightness,
music control, open an app, open a website, web search. It does NOT code, research, or do
multi-step reasoning on the desktop.

## Why

Normal agents make you watch the screen work for you. Kyuma acts mid-speech: change the song,
focus Codex, open OBS, search a quick fact — without stopping what you're saying.

## Components

- `docs/components/stt-system.md` — streaming ASR, ~1 RTF, Vosk Indian model default, swappable.
- `docs/components/kyuma-harness.md` — moderator; spawns helpers/services; terminal app + QuickShell UI.
- `docs/components/implementation-harness.md` — executes the 8 desktop capabilities.
- `docs/components/model-manager.md` — keeps Laya loaded, GPU placement, context, API, offloading.

## Flows

- `docs/flows.md` — full transcription of `Working flow.canvas` and `Kyuma harness working.canvas`.
- `docs/architecture.md` — how the four pieces connect.

## Run it

```
.venv/bin/python harness/supervisor.py start   # model + mic loop + QML overlay; --no-ui to skip overlay
.venv/bin/python harness/supervisor.py stop
```

The terminal shows every hop live: mic window → VAD chunks → STT partial/final text →
sentence → decide JSON → exec → result (`--quiet` on the loop to silence).
The loop listens on the built-in mic (`KYUMA_MIC_TARGET` overrides — set it to your
`bluez_input.…` node to use the earbuds mic instead; music will drop to HSP while
listening, that's a Bluetooth tradeoff, not a mic-quality issue). Every heard command
also pops a Hyprland toast (`harness/notifier.py`, `KYUMA_NOTIFY=0` to silence).

## Non-goals / open questions

- ~~Decision model choice (Jev vs Laya) undecided.~~ Decided: Qwen2.5-1.5B-Instruct (see above).
- No language, IPC, or protocol decided yet (Phase 01 decides). Nothing here is scaffolding — repo is empty.
- Build order is locked: `docs/PHASES/` — 16 gated phases, tests in `tests/`. No phase starts until the previous phase's goal is met AND all its gate tests pass.
