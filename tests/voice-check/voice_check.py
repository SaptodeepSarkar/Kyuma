"""Voice-pipeline check: is it the mic or the pipeline?

Two modes:
  collect: prompts you phrase by phrase ("say volume up"), records between
    two Enters, saves one wav per phrase: --collect tests/voice-check/samples
  analyze: runs the REAL chain (VAD -> STT -> buffer -> decide) on a wav or
    a whole samples dir: --wav f.wav / --analyze-dir DIR (dry-run, --act dispatches)
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


def slug(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s.lower()).strip("_")


def collect(samples_dir: str, phrases: list[str], target: str | None) -> list[str]:
    """Prompt per phrase, record between two Enters, save <slug>.wav."""
    os.makedirs(samples_dir, exist_ok=True)
    saved = []
    for i, phrase in enumerate(phrases):
        path = os.path.join(samples_dir, slug(phrase) + ".wav")
        print(f"[{i + 1}/{len(phrases)}] Say:  \"{phrase}\"")
        print("  NOTE: stay silent ~1s after Enter (noise calibration), then speak.")
        input("  press Enter to START recording ... ")
        cmd = ["pw-record", "--rate", "16000", "--channels", "1", "--format", "s16"]
        if target:
            cmd += ["--target", target]
        cmd.append(path)
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        input("  recording ... press Enter to STOP ... ")
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        size = os.path.getsize(path) if os.path.exists(path) else 0
        print(f"  saved {path} ({size // 1024} KB)")
        # Immediate capture check: all-zero file = broken chain, re-record now.
        try:
            import math as _math
            import struct as _struct
            import wave as _wave
            with _wave.open(path, "rb") as _w:
                _raw = _w.readframes(_w.getnframes())
            _s = _struct.unpack("<%dh" % (len(_raw) // 2), _raw) if _raw else (0,)
            if _s and max(abs(_x) for _x in _s) == 0:
                print("  WARNING: captured digital silence — mic chain delivered nothing; "
                      "check source (pactl list sources) and re-record this phrase")
        except Exception as _e:  # noqa: BLE001 -- never block collecting
            print(f"  (capture check skipped: {_e})")
        saved.append(path)
    print(f"done: {len(saved)} samples in {samples_dir}")
    return saved


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list-mics", action="store_true")
    ap.add_argument("--mic-target", default=None)
    ap.add_argument("--seconds", type=float, default=4.0)
    ap.add_argument("--case", type=int, default=0, help=f"0..{len(CASES) - 1}")
    ap.add_argument("--act", action="store_true", help="REALLY dispatch (acts on desktop)")
    ap.add_argument("--wav", default=None, help="skip recording, analyze this wav")
    ap.add_argument("--collect", default=None, metavar="DIR",
                    help="prompt every phrase and save one wav per phrase into DIR")
    ap.add_argument("--analyze-dir", default=None, metavar="DIR",
                    help="run the pipeline on every wav in DIR, print verdicts")
    args = ap.parse_args(argv)

    if args.list_mics:
        print("\n".join(list_mics()))
        return 0
    if shutil.which("pw-record") is None and args.wav is None and args.analyze_dir is None:
        print("pw-record not found: no mic backend")
        return 2

    target = args.mic_target or default_mic()

    if args.collect:
        phrases = [say for say, _ in CASES]
        collect(args.collect, phrases, target)
        return 0

    if args.analyze_dir:
        server = pick_server()
        print(f"server: {server or 'NONE - decide untested'}")
        wavs = sorted(f for f in os.listdir(args.analyze_dir) if f.endswith(".wav"))
        for f in wavs:
            wav = os.path.join(args.analyze_dir, f)
            say = f[:-4].replace("_", " ")
            expect = next((a for s, a in CASES if slug(s) == f[:-4]), "?")
            rep = analyze(wav, expect, server)
            print(f"--- {f} (said {say!r})")
            print(f"    STT: {rep.get('stt_text', '(none)')!r} -> {rep.get('decide')}")
            print(f"    VERDICT: {rep.get('verdict')}")
        return 0

    say, expect = CASES[args.case % len(CASES)]
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
