"""Alternating speech/silence → chunks only during speech windows.

mixed.wav = 5 × (1 s speech + 1 s silence); speech windows are
[0,1), [2,3), [4,5), [6,7), [8,9).
"""
from pathlib import Path

from stt.vad import process_wav

HERE = Path(__file__).parent
WINDOWS = [(0.0, 1.0), (2.0, 3.0), (4.0, 5.0), (6.0, 7.0), (8.0, 9.0)]
TOL = 0.35  # max allowed bleed into neighboring silence (hangover budget)


def test_mixed_chunks_only_in_speech_windows():
    calls = []

    def stub_stt(chunk):
        calls.append(chunk)

    chunks = process_wav(str(HERE / "mixed.wav"), on_chunk=stub_stt)
    assert len(chunks) == 5, f"want one chunk per speech window, got {len(chunks)}"
    assert len(calls) == len(chunks)
    for c in chunks:
        mid = (c.start + c.end) / 2
        assert any(ws <= mid < we for ws, we in WINDOWS), (
            f"chunk [{c.start:.2f}, {c.end:.2f}) mid {mid:.2f}s falls in silence")
        assert any(c.start >= ws - TOL and c.end <= we + TOL for ws, we in WINDOWS), (
            f"chunk [{c.start:.2f}, {c.end:.2f}) bleeds past hangover budget")
