"""Gate: two back-to-back sentences -> two separate emissions, no merge."""

from harness.buffer import Buffer, Word


def test_rapid_commands():
    buf = Buffer()
    emissions = []
    # First command as one burst, pause, second command as one burst, pause.
    for w, t in [("switch", 0.0), ("to", 0.05), ("workspace three", 0.10)]:
        s = buf.feed(Word(w, t))
        if s:
            emissions.append(s)
    s = buf.feed(Word("open", 1.5))  # pause fires command 1
    if s:
        emissions.append(s)
    for w, t in [("firefox", 1.55), ("now", 1.60)]:
        s = buf.feed(Word(w, t))
        if s:
            emissions.append(s)
    s = buf.feed(Word("next", 3.0))  # pause fires command 2
    if s:
        emissions.append(s)
    assert emissions == ["switch to workspace three", "open firefox now"]
    assert buf.pending == [Word("next", 3.0)]
