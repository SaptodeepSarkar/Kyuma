"""Show CleanMic input through cava and save 5s of levels to a file.

Reads (never writes) ~/.config/cava/config, overrides only the input
source and the output method in a temp copy, so your config is untouched.
Needs: cava >= 0.8 (raw ascii output), CleanMic source present.
"""
import argparse
import configparser
import os
import subprocess
import sys
import tempfile
import time

SRC_CONFIG = os.path.expanduser("~/.config/cava/config")
MAX_RANGE = 1000


def make_temp_config(source: str) -> str:
    cfg = configparser.ConfigParser()
    cfg.optionxform = str  # keep key case as-is
    cfg.read(SRC_CONFIG)
    if "input" not in cfg:
        cfg["input"] = {}
    cfg["input"]["method"] = "pulse"
    cfg["input"]["source"] = source
    if "output" not in cfg:
        cfg["output"] = {}
    cfg["output"]["method"] = "raw"
    cfg["output"]["channels"] = "mono"
    cfg["output"]["raw_target"] = "/dev/stdout"
    cfg["output"]["data_format"] = "ascii"
    cfg["output"]["ascii_max_range"] = str(MAX_RANGE)
    cfg["output"]["bar_delimiter"] = "59"   # ';'
    cfg["output"]["frame_delimiter"] = "10"  # newline
    fd, path = tempfile.mkstemp(prefix="cava-cleanmic-", suffix=".conf")
    with os.fdopen(fd, "w") as f:
        cfg.write(f)
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="CleanMic")
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--out", default=None,
                    help="levels file (default: ./cava_<source>_<ts>.txt)")
    ap.add_argument("--wav", default=None,
                    help="audio file (default: ./cava_<source>_<ts>.wav)")
    ap.add_argument("--also-raw", action="store_true",
                    help="also record raw alsa_input alongside (paired diagnosis)")
    args = ap.parse_args()

    tmp = make_temp_config(args.source)
    out_path = args.out or "cava_%s_%s.txt" % (
        args.source, time.strftime("%Y%m%d-%H%M%S"))
    wav_path = args.wav or out_path.rsplit(".", 1)[0] + ".wav"
    frames: list[str] = []
    print("showing %s for %.0fs — make some noise!" % (args.source, args.seconds),
          flush=True)
    rec = subprocess.Popen(
        ["pw-record", "--target", args.source, wav_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rec_raw = None
    if args.also_raw:
        raw_path = wav_path.rsplit(".", 1)[0] + "-raw.wav"
        rec_raw = subprocess.Popen(
            ["pw-record", "--target",
             "alsa_input.pci-0000_00_1f.3.analog-stereo", raw_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        p = subprocess.Popen(["cava", "-p", tmp],
                             stdout=subprocess.PIPE, text=True)
        end = time.time() + args.seconds
        assert p.stdout is not None
        for line in p.stdout:
            line = line.strip().strip(";")
            if not line:
                continue
            frames.append(line)
            try:
                vals = [min(int(x), MAX_RANGE) for x in line.split(";")]
            except ValueError:
                continue
            avg = sum(vals) // max(1, len(vals))
            nfill = min(20, avg * 20 // MAX_RANGE)
            bar = "#" * nfill + " " * (20 - nfill)
            peak = max(vals) if vals else 0
            sys.stdout.write("\r[%s] peak %4d" % (bar, peak))
            sys.stdout.flush()
            if time.time() >= end:
                break
        print()
    finally:
        try:
            p.terminate()
            p.wait(timeout=3)
        except Exception:
            p.kill()
        os.unlink(tmp)
        try:
            rec.terminate()
            rec.wait(timeout=5)
        except Exception:
            rec.kill()
        if rec_raw is not None:
            try:
                rec_raw.terminate()
                rec_raw.wait(timeout=5)
            except Exception:
                rec_raw.kill()
            print("saved raw   -> %s" % raw_path)

    with open(out_path, "w") as f:
        f.write("\n".join(frames) + "\n")
    peak_all = 0
    for ln in frames:
        for x in ln.split(";"):
            try:
                peak_all = max(peak_all, int(x))
            except ValueError:
                pass
    print("saved %d frames -> %s (peak %d/%d)%s"
          % (len(frames), out_path, peak_all, MAX_RANGE,
             " — mic is LIVE" if peak_all > 0 else " — all zeros, mic SILENT"))
    try:
        import struct
        import wave as wavmod
        w = wavmod.open(wav_path)
        n = w.getnframes()
        raw = w.readframes(n)
        vals = struct.unpack("<" + "h" * (len(raw) // 2), raw) if raw else ()
        skip = int(w.getframerate() * 0.25)
        vals = vals[skip:]
        import math
        rms = math.sqrt(sum(v * v for v in vals) / max(1, len(vals))) \
            if vals else 0
        pk = max(abs(v) for v in vals) if vals else 0
        print("saved audio -> %s (RMS=%.0f peak=%d)" % (wav_path, rms, pk))
    except Exception as e:
        print("audio save FAILED (%s) — is pw-record installed?" % e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
