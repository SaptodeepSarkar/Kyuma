"""Gate: VAD-silence chunk (zeros) yields no words."""

from stt.stream import SAMPLE_RATE, StreamingRecognizer


def test_silence_empty(model):
    rec = StreamingRecognizer(model)
    silence = b"\x00" * SAMPLE_RATE * 2 * 2  # 2s of 16-bit silence
    for i in range(0, len(silence), 4000):
        partial, final = rec.push(silence[i : i + 4000])
        assert partial == [] and final == [], f"words out on silence at chunk {i // 4000}"
    assert rec.finalize() == [], "finalize flushed words from pure silence"
