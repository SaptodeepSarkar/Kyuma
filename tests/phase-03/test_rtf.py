"""Gate: realtime factor <= ~1.2 on the sample audio."""

import time
import wave

import pytest

from stt.stream import transcribe_wav

from conftest import SAMPLE_WAV


def test_rtf(model):
    with wave.open(SAMPLE_WAV, "rb") as wf:
        duration = wf.getnframes() / wf.getframerate()
    assert duration > 0
    start = time.monotonic()
    n_words = sum(len(w) for k, w in transcribe_wav(SAMPLE_WAV, model) if k == "final")
    rtf = (time.monotonic() - start) / duration
    print(f"\nRTF={rtf:.3f} ({duration:.1f}s audio, {n_words} final words)")
    if n_words == 0:
        pytest.skip("no words decoded; RTF meaningless")
    assert rtf <= 1.2, f"RTF {rtf:.3f} exceeds ~1.2"
