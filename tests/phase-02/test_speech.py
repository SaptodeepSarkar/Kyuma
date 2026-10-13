"""Speech file → at least one chunk emitted (each reaches the STT stub)."""
from pathlib import Path

from stt.vad import process_wav

HERE = Path(__file__).parent


def test_speech_emits_chunks():
    calls = []

    def stub_stt(chunk):
        calls.append(chunk)

    chunks = process_wav(str(HERE / "speech.wav"), on_chunk=stub_stt)
    assert len(chunks) >= 1, "speech file produced no chunks"
    assert len(calls) == len(chunks), "every chunk must reach STT exactly once"
    for c in chunks:
        assert 0.0 <= c.start < c.end <= 2.0 + 1e-6
        assert len(c.pcm) > 0
