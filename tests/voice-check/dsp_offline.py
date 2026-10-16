"""Offline LADSPA harness: run a wav through cleanmic-dsp.so and measure.

Answers: does the chain actually suppress the constant hash while keeping
speech? Prints per-100ms RMS for input vs output so silence/speech are
visibly separated.
"""
from __future__ import annotations

import ctypes
import os
import struct
import subprocess
import sys
import wave

SO = os.path.expanduser("~/.local/lib/ladspa/cleanmic-dsp.so")
CU = ctypes.c_ulong
CS = ctypes.c_char_p
F = ctypes.c_float
VP = ctypes.c_void_p


class Desc(ctypes.Structure):
    _fields_ = [
        ("uid", CU), ("label", CS), ("props", CU), ("name", CS), ("maker", CS),
        ("copy", CS), ("nports", CU), ("pdesc", ctypes.POINTER(ctypes.c_int)),
        ("pnames", ctypes.POINTER(CS)), ("hints", VP), ("impl", VP),
        ("inst", VP), ("conn", VP), ("act", VP), ("run", VP), ("runadd", VP),
        ("setgain", VP), ("deact", VP), ("cleanup", VP),
    ]


def load(label_wanted: str):
    lib = ctypes.CDLL(SO)
    lib.ladspa_descriptor.restype = ctypes.POINTER(Desc)
    inst_t = ctypes.CFUNCTYPE(VP, VP, CU)
    conn_t = ctypes.CFUNCTYPE(None, VP, CU, ctypes.POINTER(F))
    run_t = ctypes.CFUNCTYPE(None, VP, CU)
    for i in range(4):
        d = lib.ladspa_descriptor(i)
        if not d:
            break
        desc = d.contents
        if desc.label.decode() != label_wanted:
            continue
        h = inst_t(desc.inst)(ctypes.byref(desc), 48000)
        return desc, h, conn_t(desc.conn), run_t(desc.run)
    raise SystemExit(f"label {label_wanted} not found in {SO}")


def to_48k_mono_float(path: str) -> list[float]:
    tmp = "/tmp/offline48.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-ar", "48000",
                    "-ac", "1", "-c:a", "pcm_s16le", tmp], check=True)
    with wave.open(tmp, "rb") as w:
        raw = w.readframes(w.getnframes())
    return [x / 32768.0 for x in struct.unpack("<%dh" % (len(raw) // 2), raw)]


def seg_rms(v: list[float], n: int = 4800) -> list[int]:
    out = []
    for i in range(0, len(v), n):
        s = v[i:i + n]
        out.append(int((sum(x * x for x in s) / len(s)) ** 0.5 * 32768))
    return out


def run_chain(x: list[float], block: int = 480) -> list[float]:
    """rnnoise -> limiter, exactly as the PipeWire graph does."""
    rn_desc, rn_h, rn_conn, rn_run = load("cleanmic_rnnoise")
    lim_desc, lim_h, lim_conn, lim_run = load("cleanmic_limiter")
    n = len(x) + 4096
    buf_in = (F * n)()
    buf_mid = (F * n)()
    buf_out = (F * n)()
    for i, v in enumerate(x):
        buf_in[i] = v
    thr = F(50.0)
    rn_conn(rn_h, 0, buf_in)
    rn_conn(rn_h, 1, buf_mid)
    rn_conn(rn_h, 2, ctypes.pointer(thr))
    off = 0
    while off < len(x):
        rn_run(rn_h, min(block, len(x) - off))
        off += block
    ceil = F(-3.0)
    lim_conn(lim_h, 0, buf_mid)
    lim_conn(lim_h, 1, buf_out)
    lim_conn(lim_h, 2, ctypes.pointer(ceil))
    off = 0
    while off < len(x):
        lim_run(lim_h, min(block, len(x) - off))
        off += block
    return [buf_out[i] for i in range(len(x))]


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else \
        "tests/voice-check/samples3/volume_up.wav"
    x = to_48k_mono_float(src)
    y = run_chain(x)
    print(f"file: {src}  samples: {len(x)}")
    print("in :", seg_rms(x))
    print("out:", seg_rms(y))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
