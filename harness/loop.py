"""Phase 14 — harness loop: buffer -> decide -> dispatch -> flush.

Wiring for flows.md harness-loop steps 2-7, scripted (no live mic): callers
feed STT ``Word`` batches; ``run_once`` buffers them, dispatches every
completed sentence, and flushes the consumed words on 200 AND on error.
Words that arrive mid-decide (slow model) belong to the next command and are
kept — flush removes only the dispatched sentence's words, by identity.

Importing this module registers the real executor handlers (the only
production caller of ``register_all``); gate 07 stays green because
``executor/__init__`` itself has no import-time side effects.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import urllib.request
from typing import Any, Callable

import executor
from executor.dispatch import dispatch
from harness.buffer import Buffer
from harness.contracts import Exec, Result, Word

SERVER_ENV = "KYUMA_MODEL_SERVER"
DEFAULT_SERVER = "http://127.0.0.1:8081"
DECIDE_TIMEOUT = 60.0

NOOP = "noop"

DecideFn = Callable[[str], dict[str, Any]]

executor.register_all()

_BUFFER = Buffer()


def reset_buffer() -> None:
    """Drop all buffered words (test isolation)."""
    global _BUFFER
    _BUFFER = Buffer()


def pending_words() -> list[Word]:
    """Words buffered but not yet dispatched (next command's fragment)."""
    return _BUFFER.pending


def ingest(words: list[Word]) -> list[str]:
    """Buffer words; return completed sentences without deciding/dispatching."""
    sentences: list[str] = []
    for w in words:
        sentence = _BUFFER.feed(w)
        if sentence is not None:
            sentences.append(sentence)
    return sentences


def http_decide(base: str, sentence: str, timeout: float = DECIDE_TIMEOUT) -> dict[str, Any]:
    """POST one sentence to a model-server wrapper ``/decide``; return Exec dict."""
    body = json.dumps({"sentence": sentence}).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/decide",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.load(resp)
    except Exception as e:  # noqa: BLE001 -- transport failure becomes an error Result
        raise RuntimeError(f"model server {base} unreachable: {e}") from e
    if not isinstance(payload, dict) or "action" not in payload:
        detail = payload.get("error", payload) if isinstance(payload, dict) else payload
        raise ValueError(f"model server refused {sentence!r}: {detail}")
    return payload


def _default_decide(sentence: str) -> dict[str, Any]:
    return http_decide(os.environ.get(SERVER_ENV, DEFAULT_SERVER), sentence)


def _log(log: list[dict[str, Any]] | None, hop: str, detail: str = "") -> None:
    if log is not None:
        log.append({"t": time.time(), "hop": hop, "detail": detail})


def _force_emit() -> str | None:
    """Utterance-end: emit leftover words as one sentence (VAD-silence boundary)."""
    leftover = _BUFFER.pending
    if not leftover:
        return None
    # Buffer has no public drain; same-package clear of exactly these words.
    _BUFFER._words.clear()  # noqa: SLF001
    sentence = " ".join(w.w for w in leftover).strip().rstrip(".!?").strip()
    return sentence or None


def run_once(
    words: list[Word],
    decide_fn: DecideFn | None = None,
    log: list[dict[str, Any]] | None = None,
) -> Result | None:
    """Buffer ``words``, dispatch each completed sentence, flush, answer.

    Returns the last dispatch ``Result``, or None when nothing completed.
    Never raises: decide/transport failures become error Results. Every hop
    appends ``{t, hop, detail}`` to ``log`` when given (feeds Phase 16).
    """
    decide = decide_fn or _default_decide
    words = list(words)
    _log(log, "words", f"{len(words)} words")
    if words:
        _BUFFER.check_timeout(words[0].t)  # stalled fragment discarded, nothing emitted
    sent = _BUFFER.pending + words  # refs kept: flush removes exactly these, by identity
    sent_ids = {id(w) for w in sent}
    sentences = ingest(words)
    tail = _force_emit()
    if tail is not None:
        sentences.append(tail)
    for sentence in sentences:
        _log(log, "sentence", sentence)
    result: Result | None = None
    for sentence in sentences:
        try:
            obj = decide(sentence)
            _log(log, "decide", json.dumps(obj)[:200])
            if isinstance(obj, dict) and obj.get("action") == NOOP:
                result = Result(code=200, detail=f"noop: {sentence!r} is not a command")
            else:
                exec_ = Exec.from_dict(obj)
                _log(log, "exec", f"{exec_.action} {exec_.args}")
                result = dispatch(exec_)
        except Exception as e:  # noqa: BLE001 -- loop never drops speech on errors
            result = Result(code="error", detail=f"decide failed: {e}")
        _log(log, "result", f"{result.code} {result.detail}")
        # Flush consumed words on 200 AND error; words appended mid-decide
        # (slow model) have fresh ids and survive.
        _BUFFER._words[:] = [w for w in _BUFFER._words if id(w) not in sent_ids]  # noqa: SLF001
    return result


# Prompt-to-handler arg aliases. The decision prompt (decide_prompt.py,
# frozen by the Phase 06 bake-off) emits these keys; handlers read those.
# Normalization lives here so neither side changes. shortcut: per-action
# required-arg checks, when an executor phase needs them.
_ALIASES: dict[str, dict[str, str]] = {
    "open_app": {"app": "name"},
    "focus_app": {"app": "class"},
    "open_website": {"site": "url"},
    "focus_website": {"site": "query"},
    "switch_workspace": {"workspace": "n"},
    "focus_window": {"window": "title"},
    "brightness": {"level": "value"},
    "volume": {"command": "op"},
    "music": {"command": "op"},
}


def normalize(action: str, args: dict[str, Any]) -> dict[str, Any]:
    """Rewrite prompt-style arg keys to handler-style keys (copy, no mutate)."""
    mapping = _ALIASES.get(action, {})
    out = {mapping.get(k, k): v for k, v in args.items()}
    # Drop prompt-echo artifacts (model sometimes copies "/no_think" in).
    out = {k: v for k, v in out.items()
           if not (isinstance(v, str) and "no_think" in v)}
    # Model sometimes drops "op" but gives the payload: infer set.
    if action in ("volume", "brightness", "music") and "op" not in out:
        if "level" in out or "value" in out:
            out["op"] = "set"
    return out


def decide_normalized(decide_fn: DecideFn) -> DecideFn:
    """Wrap a decide fn so every Exec dict gets normalized args."""

    def wrap(sentence: str) -> dict[str, Any]:
        obj = decide_fn(sentence)
        if isinstance(obj, dict) and isinstance(obj.get("args"), dict):
            obj = {**obj, "args": normalize(str(obj.get("action")), obj["args"])}
        return obj

    return wrap


def write_state(state_file: str, listening: bool, last: Result | None,
                sentence: str = "") -> None:
    """State file the QuickShell overlay polls (atomic replace)."""
    tmp = state_file + ".tmp"
    with open(tmp, "w") as f:
        json.dump({
            "listening": listening,
            "last_sentence": sentence,
            "last_action": (last.detail if last else ""),
            "result": (str(last.code) if last else ""),
            "ts": time.time(),
        }, f)
    os.replace(tmp, state_file)


def _default_mic_target() -> str | None:
    """Built-in (non-Bluetooth) mic node name, or None for pw-record default.

    Never default to a bluez_input source: capturing from a BT headset mic
    forces the HSP/HFP profile and wrecks playback quality (2026-10-13).
    """
    import shutil
    import subprocess

    pactl = shutil.which("pactl")
    if pactl is None:
        return None
    try:
        out = subprocess.run([pactl, "list", "sources", "short"],
                             capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001
        return None
    lines = out.splitlines()
    for ln in lines:  # our filtered mic wins when present
        if "\tCleanMic" in ln and "Limited" not in ln:
            return ln.split()[1]
    alsa = [ln.split()[1] for ln in lines if "\talsa_input." in ln]
    if alsa:
        return alsa[0]
    non_bt = [ln.split()[1] for ln in lines
              if "bluez" not in ln and "monitor" not in ln]
    return non_bt[0] if non_bt else None


def _say(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(f"[loop] {msg}", flush=True)


def listen_once(model, decide_fn: DecideFn, state_file: str,
                window_s: float = 2.0, base_t: float = 0.0,
                log: list[dict[str, Any]] | None = None,
                mic_target: str | None = None,
                verbose: bool = True) -> tuple[Result | None, float]:
    """One mic window: capture -> VAD -> STT -> run_once -> state file.

    Silence yields no chunks: run_once([]) force-emits leftovers, so short
    commands act on pause. Returns (result, new_base_t).
    """
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from stt import vad as vad_mod
    from stt.stream import StreamingRecognizer

    _say(f"mic window {window_s:.1f}s on {mic_target or 'default source'} ...", verbose)
    chunks = vad_mod.capture_live(duration_s=window_s, target=mic_target)
    if not chunks:
        _say("VAD: silence, no speech chunks", verbose)
    words: list[Word] = []
    if chunks:
        _say("VAD: %d speech chunk(s): %s" % (
            len(chunks), ", ".join(f"{c.end - c.start:.2f}s" for c in chunks)), verbose)
        rec = StreamingRecognizer(model)
        for c in chunks:
            for off in range(0, len(c.pcm), 8000):  # ~0.25s slices: live partials
                partials, finals = rec.push(c.pcm[off:off + 8000])
                if partials:
                    _say("STT partial: " + " ".join(w.w for w in partials), verbose)
                words.extend(Word(w.w, base_t + w.t) for w in finals)
        words.extend(Word(w.w, base_t + w.t) for w in rec.finalize())
        _say("STT final: " + (" ".join(w.w for w in words) or "(nothing)"), verbose)
    log_list: list[dict[str, Any]] = []
    result = run_once(words, decide_fn=decide_fn, log=log_list)
    if log is not None:
        log.extend(log_list)
    for e in log_list:
        if e["hop"] in ("sentence", "decide", "exec", "result"):
            _say(f"{e['hop']}: {e['detail']}", verbose)
    sentences = [e["detail"] for e in log_list if e["hop"] == "sentence"]
    if sentences:
        from harness import notifier as notifier_mod
        notifier_mod.heard(sentences[-1])
        if result is not None:
            notifier_mod.acted(f"{result.code}: {result.detail}"[:200],
                               ok=result.code == 200)
    write_state(state_file, True, result, sentences[-1] if sentences else "")
    return result, base_t + window_s


def main(argv: list[str] | None = None) -> int:
    """Live loop entry for the supervisor: `python harness/loop.py [--once]."""
    import argparse
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from stt.loader import load_model

    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--window", type=float, default=2.0)
    ap.add_argument("--server", default=os.environ.get(SERVER_ENV, DEFAULT_SERVER))
    ap.add_argument("--state", default=os.environ.get("KYUMA_STATE_FILE", "/tmp/kyuma-state.json"))
    ap.add_argument("--mic-target", default=os.environ.get("KYUMA_MIC_TARGET", None))
    ap.add_argument("--quiet", action="store_true",
                    help="only errors to stdout (default: log every hop)")
    args = ap.parse_args(argv)
    verbose = not args.quiet

    mic_target = args.mic_target or _default_mic_target()

    _say(f"loading STT model ...", verbose)
    model = load_model()
    _say(f"STT ready; mic={mic_target or 'default'} server={args.server} "
         f"window={args.window}s state={args.state}", verbose)
    decide_fn = decide_normalized(lambda s: http_decide(args.server, s))
    write_state(args.state, True, None, "")
    base = 0.0
    while True:
        try:
            _, base = listen_once(model, decide_fn, args.state, args.window, base,
                                  mic_target=mic_target, verbose=verbose)
        except Exception as e:  # noqa: BLE001 -- loop never dies on mic errors
            write_state(args.state, False, Result(code="error", detail=str(e)[:200]))
        if args.once:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
