"""Offline mic cleanup: DC-block -> spectral gate -> hard noise gate (true silence).

Stdlib only (handwritten radix-2 FFT). Two stages, tuned for the observed
failure (constant ~20k RMS hash that suppression alone would smear into speech):
  1. DC blocker + spectral subtraction against a noise profile taken from the
     quietest 300ms (over-subtraction, -50dB floor: no musical noise).
  2. Broadband expander AFTER cleanup: frame energy below the noise floor is
     hard-zeroed (TRUE silence); 250ms hangover + soft knee so speech onsets
     survive. Speech is never attenuated, only silence is deleted.

Usage: voice_check.py --denoise in.wav out.wav [--noise-ms 300] [--gate-db 12]
"""
from __future__ import annotations

import argparse
import cmath
import math
import struct
import wave

RATE = 16000
N = 512
HOP = 256


def fft(a: list[complex]) -> list[complex]:
    n = len(a)
    j = 0
    for i in range(1, n):
        b = n >> 1
        while j & b:
            j ^= b
            b >>= 1
        j ^= b
        if i < j:
            a[i], a[j] = a[j], a[i]
    m = 2
    while m <= n:
        wm = cmath.exp(-2j * cmath.pi / m)
        k = 0
        while k < n:
            wj = 1.0
            for jj in range(m // 2):
                t = wj * a[k + jj + m // 2]
                u = a[k + jj]
                a[k + jj] = u + t
                a[k + jj + m // 2] = u - t
                wj *= wm
            k += m
        m *= 2
    return a


def ifft(a: list[complex]) -> list[complex]:
    n = len(a)
    out = fft([x.conjugate() for x in a])
    return [x.conjugate() / n for x in out]


HANN = [0.5 - 0.5 * math.cos(2 * math.pi * i / N) for i in range(N)]


def frame_rms(s: list[float]) -> float:
    return math.sqrt(sum(x * x for x in s) / len(s)) if s else 0.0


def denoise(path_in: str, path_out: str, noise_ms: int = 300, gate_db: float = 12.0,
            floor_db: float = -50.0, profile_from: str | None = None) -> dict:
    with wave.open(path_in, "rb") as w:
        assert w.getframerate() == RATE and w.getnchannels() == 1, "need 16kHz mono"
        raw = w.readframes(w.getnframes())
    s = [float(x) / 32768.0 for x in struct.unpack("<%dh" % (len(raw) // 2), raw)]

    # 1. DC blocker (one-pole highpass ~30Hz): kills rail-slam + rumble.
    dc = 0.0
    out = []
    for x in s:
        dc = 0.995 * dc + 0.005 * x
        out.append(x - dc)
    s = out

    # 2. Frame + spectrum.
    frames = []
    for st in range(0, max(1, len(s) - N), HOP):
        frames.append([s[st + i] * HANN[i] for i in range(N)])
    specs = [fft([complex(v, 0) for v in fr]) for fr in frames]
    mags = [[abs(b) for b in sp[: N // 2 + 1]] for sp in specs]

    # 3. Noise profile = mean spectrum of quietest `noise_ms` — from THIS
    # file, or borrowed from a calibration clip recorded in the same session
    # (same mic, same room) when this clip has no clean silence of its own.
    prof_src, prof_mags, prof_frames = mags, mags, frames
    if profile_from is not None:
        with wave.open(profile_from, "rb") as w:
            praw = w.readframes(w.getnframes())
        ps = [float(x) / 32768.0 for x in struct.unpack("<%dh" % (len(praw) // 2), praw)]
        dc = 0.0
        psd = []
        for x in ps:
            dc = 0.995 * dc + 0.005 * x
            psd.append(x - dc)
        pframes = []
        for st in range(0, max(1, len(psd) - N), HOP):
            pframes.append([psd[st + i] * HANN[i] for i in range(N)])
        pspecs = [fft([complex(v, 0) for v in fr]) for fr in pframes]
        prof_src = [[abs(b) for b in sp[: N // 2 + 1]] for sp in pspecs]
        prof_frames = pframes
    need = max(1, int(noise_ms / 1000 * RATE / HOP))
    order = sorted(range(len(prof_frames)), key=lambda i: frame_rms(prof_frames[i]))
    prof = [0.0] * (N // 2 + 1)
    for i in order[:need]:
        for b in range(len(prof)):
            prof[b] += prof_src[i][b]
    prof = [p / need for p in prof]

    # 4. Over-subtraction with floor (kills steady hash, keeps speech bins).
    floor = 10 ** (floor_db / 20)
    clean_specs = []
    for sp, mg in zip(specs, mags):
        newsp = []
        for b in range(len(prof)):
            pwr = mg[b] ** 2
            nse = (2.0 * prof[b]) ** 2
            g = math.sqrt(max(pwr - nse, 0.0) / pwr) if pwr > 0 else 0.0
            g = max(g, floor)
            newsp.append(sp[b] * g if b < len(sp) else complex())
        full = newsp + [complex()] * (N - len(newsp))
        clean_specs.append(full)

    # 5. Overlap-add back to time domain.
    y = [0.0] * (len(frames) * HOP + N)
    for i, sp in enumerate(clean_specs):
        td = ifft(sp)
        st = i * HOP
        for j in range(N):
            y[st + j] += td[j].real * HANN[j] / (HOP / N * 1.5)

    # 6. Broadband gate with hangover: below floor -> hard zero (TRUE silence).
    #    Floor tracks the profile energy so speech (10dB+ above) always opens.
    prof_e = frame_rms([v for i in order[:need] for v in prof_frames[i]]) or 1e-6
    thr = prof_e * 10 ** (gate_db / 20)
    hang = int(0.25 * RATE / HOP)  # 250ms hangover
    open_left = 0
    gw = HOP
    gated = [0.0] * len(y)
    for i in range(0, len(y), gw):
        seg = y[i:i + gw]
        e = frame_rms(seg)
        if e > thr:
            open_left = hang
        if open_left > 0:
            gated[i:i + gw] = seg
            open_left -= 1
        # else: stays 0.0 (true silence)

    # 7. Stats + write.
    def seg_rms(v: list[float]) -> list[int]:
        n = RATE // 10
        return [int(frame_rms(v[i:i + n]) * 32768) for i in range(0, len(v), n)]

    peak = max(abs(v) for v in gated) or 1e-9
    norm = min(1.0, 0.89 / peak)  # normalize speech to -1dB, silence stays 0
    gated = [v * norm for v in gated]
    pcm = struct.pack("<%dh" % len(gated),
                      *[max(-32768, min(32767, int(v * 32768))) for v in gated])
    with wave.open(path_out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)
    return {"in_rms": seg_rms(s), "out_rms": seg_rms(gated)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("outp")
    ap.add_argument("--noise-ms", type=int, default=300)
    ap.add_argument("--gate-db", type=float, default=12.0)
    ap.add_argument("--profile-from", default=None,
                    help="borrow the noise profile from a calibration clip")
    args = ap.parse_args(argv)
    rep = denoise(args.inp, args.outp, args.noise_ms, args.gate_db,
                  profile_from=args.profile_from)
    print("in :", rep["in_rms"])
    print("out:", rep["out_rms"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
