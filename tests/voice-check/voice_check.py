"""Voice-pipeline check: is it the mic or the pipeline?

Tells you what to say, records it, then runs the REAL chain on your
recording (VAD -> STT -> buffer -> decide). Dry-run by default: nothing
acts on your desktop. --act also dispatches (volume WILL change etc).

 verdict logic: recording works + STT hears your words => pipeline OK,
 problem is live-mic path (source/gain). STT hears nothing => speak
 louder / pick another mic (--list-mics, --mic-target).
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import wave

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

CASES = [
    ("volume up", "volume"),
    ("mute", "volume"),
    ("switch to workspace two", "switch_workspace"),
]

SERVERS = ("http://127.0.0.1:8081", "http://127.0.0.1:8080")


def list_mics() -> list[str]:
    out = subprocess.run(["pactl", "list", "sources", "short"],
                         capture_output=True, text=True, timeout=5).stdout
    return [ln.split()[1] for ln in out.splitlines()
            if "monitor" not in ln and ln.strip()]


def default_mic() -> str | None:
    from harness.loop import _default_mic_target
    return _default_mic_target()


def record(seconds: float, target: str | None, path: str) -> None:
    cmd = ["pw-record", "--rate", "16000", "--channels", "1", "--format", "s16"]
    if target:
        cmd += ["--target", target]
    cmd.append(path)
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        proc.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)


def pick_server() -> str | None:
    import urllib.request
    for base in SERVERS:
        try:
            with urllib.request.urlopen(base + "/health", timeout=3) as r:
                if r.status == 200:
                    return base
        except Exception:  # noqa: BLE001
            continue
    return None


def analyze(wav: str, expect_action: str, server: str | None) -> dict:
    from harness.buffer import Buffer
    from harness.contracts import Word
    from stt import vad as vad_mod
    from stt.loader import load_model
    from stt.stream import StreamingRecognizer

    out: dict = {"wav": wav}
    chunks = vad_mod.process_wav(wav)
    out["vad_chunks"] = [(round(c.start, 2), round(c.end, 2)) for c in chunks]
    if not chunks:
        out["verdict"] = "VAD heard NOTHING — speak louder / check mic gain / pick another --mic-target"
        return out
    model = load_model()
    rec = StreamingRecognizer(model)
    words: list[Word] = []
    t = 0.0
    for c in chunks:
        _, finals = rec.push(c.pcm)
        words.extend(Word(w.w, t + w.t) for w in finals)
        t += (c.end - c.start)
    words.extend(Word(w.w, t) for w in rec.finalize())
    out["stt_text"] = " ".join(w.w for w in words)
    if not out["stt_text"].strip():
        out["verdict"] = "VAD fired but STT heard no words — mic too quiet/noisy for Vosk; retry closer/louder"
        return out
    buf = Buffer()
    sentences = [s for w in words if (s := buf.feed(w)) is not None]
    leftover = " ".join(w.w for w in buf.pending)
    if leftover:
        sentences.append(leftover)  # utterance-end force-emit, like the live loop
    out["sentences"] = sentences
    if server is None:
        out["verdict"] = "STT OK; no model server up (start one) so decide untested"
        return out
    from harness.loop import decide_normalized, http_decide
    decide = decide_normalized(lambda s: http_decide(server, s))
    try:
        obj = decide(sentences[0])
    except Exception:
        # No wrapper on this port (raw llama-server?): fall back to the
        # chat API + validator from model-server/decide_prompt.py.
        sys.path.insert(0, os.path.join(REPO, "model-server"))
        try:
            import decide_prompt as dpmod
        except ImportError:
            out["verdict"] = "decide FAILED: wrapper unreachable, prompt module missing"
            return out
        try:
            exec_obj = dpmod.validate_exec(dpmod.decide(server, sentences[0]))
            obj = {"action": exec_obj.action, "args": exec_obj.args}
        except ValueError:
            obj = {"action": "noop", "args": {}}
        except Exception as e:  # noqa: BLE001
            out["verdict"] = f"decide FAILED: {e}"
            return out
    out["decide"] = obj
    got = obj.get("action")
    if got == expect_action:
        out["verdict"] = f"PIPELINE OK — heard you, correct action ({got})"
    elif got == "noop":
        out["verdict"] = f"STT heard '{out['stt_text']}' but model declined (noop) — enunciate the command shape from the prompt"
    else:
        out["verdict"] = f"STT OK but wrong action: got {got}, want {expect_action}"
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list-mics", action="store_true")
    ap.add_argument("--mic-target", default=None)
    ap.add_argument("--seconds", type=float, default=4.0)
    ap.add_argument("--case", type=int, default=0, help=f"0..{len(CASES) - 1}")
    ap.add_argument("--act", action="store_true", help="REALLY dispatch (acts on desktop)")
    ap.add_argument("--wav", default=None, help="skip recording, analyze this wav")
    args = ap.parse_args(argv)

    if args.list_mics:
        print("\n".join(list_mics()))
        return 0
    if shutil.which("pw-record") is None:
        print("pw-record not found: no mic backend")
        return 2

    say, expect = CASES[args.case % len(CASES)]
    target = args.mic_target or default_mic()
    server = pick_server()
    print(f"mic: {target or 'default'} | server: {server or 'NONE - decide untested'}")

    if args.wav:
        wav = args.wav
    else:
        fd, wav = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        print(f"SAY (in ~1s, clearly):  \"{say}\"")
        import time
        time.sleep(1.0)
        print(f"recording {args.seconds:.0f}s ...")
        record(args.seconds, target, wav)
        print("recorded.")

    rep = analyze(wav, expect, server)
    print(f"VAD chunks: {rep.get('vad_chunks')}")
    print(f"STT text:   {rep.get('stt_text', '(none)')!r}")
    print(f"sentences:  {rep.get('sentences')}")
    print(f"decide:     {rep.get('decide')}")
    print("VERDICT:", rep.get("verdict"))

    if args.act and rep.get("decide", {}).get("action") not in (None, "noop"):
        from executor.dispatch import dispatch
        from harness.contracts import Exec
        from harness.loop import normalize
        obj = rep["decide"]
        r = dispatch(Exec(action=obj["action"], args=normalize(obj["action"], obj["args"])))
        print(f"ACTION: {r.code} {r.detail}")
    elif args.act:
        print("ACTION: skipped (no valid Exec)")
    if not args.wav:
        os.unlink(wav)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
