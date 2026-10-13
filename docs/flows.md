# Flows (transcribed from vault canvases)

> These are **Obsidian canvas files** — view them in Obsidian at
> `Projects/Kyuma/Flows/Working flow.canvas` and
> `Projects/Kyuma/Flows/Kyuma harness working.canvas` in the Agents vault.
> Below is a text transcription for agents working outside Obsidian; the canvases are canonical.

## 1. System flow — `Flows/Working flow.canvas`

Chain: Laya Model Manager → Laya interface → Kyuma Harness → Implementation Harness.
The manager owns the model and its API; the harness is the only consumer of that API;
the executor is the only thing the harness drives.

## 2. Harness loop — `Flows/Kyuma harness working.canvas`, step by step

1. VAD gates the mic: silence → "Nothing is Spoken" → no text output, back to listening.
2. Speech → "A word is spoken" → STT transcribes → word reaches Kyuma Harness.
3. Harness asks: "The word (+ buffer) makes sense?" — i.e. is it a full command/sentence yet?
4. No → append word to ARRAY/storage, wait for next word (loop to step 2).
5. Yes → call Model Manager API with the buffered sentence, wait for response.
6. Convert response to valid exec format/code → send to Implementation Harness.
7. Executor returns 200 or error → flush the ARRAY either way → back to listening.

## Tiny details worth preserving

- Silence and speech are separate VAD/STT paths; silence emits nothing (no empty calls).
- Buffering is append-only until a decision fires; no partial dispatch.
- Flush-on-both-outcomes: no stale words leak into the next command.
- The model call is the only blocking wait in the loop; everything else streams.
