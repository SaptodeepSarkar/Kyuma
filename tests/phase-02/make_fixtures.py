"""Synthesize Phase 02 fixture wavs with stdlib only (no downloads).

- silence.wav: 5 s digital silence
- speech.wav:  2 s dual-tone "voice-ish" signal (440 + 660 Hz)
- mixed.wav:   10 s alternating 1 s speech / 1 s silence (5 speech windows)
All 16 kHz mono 16-bit PCM.
"""
import math
import struct
import wave
from pathlib import Path

SR = 16000
AMP = 12000
HERE = Path(__file__).parent


def _tone(n: int) -> bytes:
    return struct.pack(
        "<%dh" % n,
        *[int(AMP * 0.7 * math.sin(2 * math.pi * 440 * i / SR)
              + AMP * 0.3 * math.sin(2 * math.pi * 660 * i / SR))
          for i in range(n)],
    )


def _write(name: str, payload: bytes) -> None:
    with wave.open(str(HERE / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(payload)


def main() -> None:
    _write("silence.wav", b"\x00" * SR * 5 * 2)
    _write("speech.wav", _tone(SR * 2))
    parts = []
    for _ in range(5):
        parts += [_tone(SR), b"\x00" * SR * 2]
    _write("mixed.wav", b"".join(parts))
    print("wrote", sorted(p.name for p in HERE.glob("*.wav")))


if __name__ == "__main__":
    main()
