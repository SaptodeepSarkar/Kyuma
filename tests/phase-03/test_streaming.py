"""Gate: partials stream out BEFORE any final (streaming, not batch)."""

from stt.stream import transcribe_wav

from conftest import SAMPLE_WAV


def test_partials_before_final(model):
    kinds = []
    n_partial_words = 0
    n_final_words = 0
    for kind, words in transcribe_wav(SAMPLE_WAV, model):
        kinds.append(kind)
        if kind == "partial":
            n_partial_words += len(words)
        else:
            n_final_words += len(words)
    assert kinds, "no events at all from sample audio"
    assert "partial" in kinds and "final" in kinds, f"need both event types, got {set(kinds)}"
    assert kinds.index("partial") < kinds.index("final"), "first partial must precede first final"
    assert n_final_words > 0, "final transcript is empty"
