"""Gate: stalled fragment is DISCARDED after timeout (nothing emitted)."""

from harness.buffer import Buffer, Word


def test_timeout_discards():
    buf = Buffer(timeout_s=2.0)
    assert buf.feed(Word("switch", 0.0)) is None
    buf.check_timeout(2.5)  # stall past timeout
    assert buf.pending == []
    # Fresh word after a stall starts a new batch; stale word does not leak in.
    assert buf.feed(Word("to", 10.0)) is None
    assert [w.w for w in buf.pending] == ["to"]


def test_timeout_via_feed():
    buf = Buffer(timeout_s=2.0)
    buf.feed(Word("switch", 0.0))
    buf.feed(Word("to", 10.0))  # arrives stale -> old fragment discarded first
    assert [w.w for w in buf.pending] == ["to"]
