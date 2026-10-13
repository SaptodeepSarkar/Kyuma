"""5 s silence file → zero STT invocations (stub counter)."""
from pathlib import Path

from stt.vad import process_wav

HERE = Path(__file__).parent


def test_silence_emits_nothing():
    calls = []

    def stub_stt(chunk):
        calls.append(chunk)

    chunks = process_wav(str(HERE / "silence.wav"), on_chunk=stub_stt)
    assert chunks == []
    assert calls == [], f"silence made {len(calls)} STT call(s), want 0"
