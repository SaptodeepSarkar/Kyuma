"""Gate: fragments accumulate -> one sentence out, not three (pause fires it)."""

from harness.buffer import Buffer, Word


def test_accumulate():
    buf = Buffer()
    # Burst: rapid STT words accumulate silently (no 3-word prefix fire).
    assert buf.feed(Word("switch", 0.0)) is None
    assert buf.feed(Word("to", 0.05)) is None
    assert buf.feed(Word("workspace three", 0.10)) is None
    # Next word after a pause ends the command -> whole sentence out.
    sentence = buf.feed(Word("volume", 1.5))
    assert sentence == "switch to workspace three"
    assert buf.pending == [Word("volume", 1.5)]  # fresh batch holds the new word
