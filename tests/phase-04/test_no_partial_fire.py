"""Gate: a single word emits nothing downstream (silence, not dispatch)."""

from harness.buffer import Buffer, Word


def test_no_partial_fire():
    buf = Buffer()
    assert buf.feed(Word("switch", 0.0)) is None
    assert buf.pending != []  # buffered, not dropped: still waiting
    assert [w.w for w in buf.pending] == ["switch"]
