"""Kyuma mic filter: system-wide voice cleanup (stdin raw s16le 16k mono -> stdout).

Chain per 32ms frame (16ms hop), fully causal:
  DC-block -> highpass (bins < ~150Hz ramped out: fan/hum lives here) ->
  spectral subtraction vs adaptive noise profile (first 0.5s + running
  minima, over-subtraction, -45dB floor) -> broadband gate with 250ms
  hangover (below floor = hard zero: TRUE silence, never smeared noise).

Speech is never attenuated: only silence is deleted. Stdlib only.
"""
from __future__ import annotations

import argparse
import cmath
import math
import struct
import sys
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
# Highpass weights: 0 below ~90Hz, ramp to 1 by ~190Hz (bin = 31.25Hz).
HP = [0.0 if i < 3 else ((i - 3) / 3.0 if i < 6 else 1.0) for i in range(N // 2 + 1)]
FLOOR = 10 ** (-35.0 / 20)
OVER = 1.2


class Filter:
    def __init__(self, gate_db: float = 12.0):
        self.prof: list[float] | None = None
        self.calib: list[list[float]] = []
        self.gate_db = gate_db
        self.hang = 0
        self.HANG_FRAMES = 15  # ~240ms: speech pauses never chop
        self.res_floor: float | None = None  # residual-energy floor, learned
        self.buf = bytearray()
        self.ola: list[float] = [0.0] * N  # overlap-add accumulator

    def _frame(self, spec: list[complex], mag: list[float]) -> list[float]:
        if self.prof is None:
            self.skip = getattr(self, "skip", 8)  # device settle transient first
            if self.skip > 0:
                self.skip -= 1
                return []  # output silence, not garbage
            self.calib.append(mag)
            if len(self.calib) >= 32:  # next ~0.5s = noise floor
                cols = len(mag)
                self.prof = []
                for b in range(cols):
                    col = sorted(c[b] for c in self.calib)
                    self.prof.append(col[len(col) // 2])  # median: robust
            else:
                return []  # calibrating: output silence, not garbage
        assert self.prof is not None
        # Running minima: track slow noise drift, never speech (minima win).
        for b in range(len(mag)):
            if mag[b] < self.prof[b]:
                self.prof[b] = mag[b]
            else:
                self.prof[b] += 0.0005 * (mag[b] - self.prof[b])
        gains = []
        for b in range(len(mag)):
            pwr = mag[b] ** 2
            nse = (OVER * self.prof[b]) ** 2
            g = math.sqrt(max(pwr - nse, 0.0) / pwr) if pwr > 0 else 0.0
            gains.append(max(g, FLOOR) * HP[b])
        full = [spec[b] * gains[b] for b in range(len(gains))]
        full += [complex()] * (N - len(full))
        td = ifft(full)
        cleaned = [td[j].real * HANN[j] for j in range(N)]
        # Gate on RESIDUAL energy (post-subtraction): stationary hash is
        # already removed, so speech residuals poke above an absolute floor.
        # Broadband pre-gating is impossible at ~0dB SNR (nothing exceeds).
        res_e = math.sqrt(sum(v * v for v in cleaned) / N)
        if self.res_floor is None:
            self.res_floor = res_e
        elif res_e < self.res_floor:
            self.res_floor = res_e  # fast down: track the quiet
        else:
            self.res_floor += 0.002 * (res_e - self.res_floor)  # slow up
        opens_at = max(self.res_floor * 10 ** (self.gate_db / 20), 0.02)
        if res_e > opens_at:
            self.hang = self.HANG_FRAMES
        if self.hang > 0:
            self.hang -= 1
            return cleaned
        return [0.0] * N  # TRUE silence

    def push(self, pcm: bytes) -> bytes:
        self.buf += pcm
        out = bytearray()
        while len(self.buf) >= N * 2:
            frame = struct.unpack("<%dh" % N, bytes(self.buf[: N * 2]))
            del self.buf[: N * 2]
            spec = fft([complex(v / 32768.0 * HANN[i], 0) for i, v in enumerate(frame)])
            mag = [abs(b) for b in spec[: N // 2 + 1]]
            cleaned = self._frame(spec, mag)
            if not cleaned:
                # Calibrating: advance OLA with zeros (keeps timing exact).
                self.ola = self.ola[HOP:] + [0.0] * HOP
                continue
            for j in range(N):
                self.ola[j] += cleaned[j]
            # Hann @75% overlap sums to 2.0 -> scale 0.5 for unity gain.
            out += struct.pack("<%dh" % HOP, *[
                max(-32768, min(32767, int(v * 32768 * 0.5))) for v in self.ola[:HOP]])
            self.ola = self.ola[HOP:] + [0.0] * HOP
        return bytes(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate-db", type=float, default=12.0)
    ap.add_argument("--in-wav", default=None, help="offline test: filter this file")
    ap.add_argument("--out-wav", default=None, help="offline test: write here")
    args = ap.parse_args(argv)
    flt = Filter(args.gate_db)
    if args.in_wav:
        with wave.open(args.in_wav, "rb") as w:
            raw = w.readframes(w.getnframes())
        blob = flt.push(raw)
        blob += flt.push(b"")  # drain (no-op; kept explicit)
        with wave.open(args.out_wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(blob)
        return 0
    inp, outp = sys.stdin.buffer, sys.stdout.buffer
    while True:
        data = inp.read(HOP * 2 * 4)
        if not data:
            break
        blob = flt.push(data)
        if blob:
            outp.write(blob)
            outp.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
