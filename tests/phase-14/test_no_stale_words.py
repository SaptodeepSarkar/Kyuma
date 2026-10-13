"""No stale words: two rapid commands, second uses only its own words."""
from harness import loop as harness_loop


def test_rapid_commands_isolated(words):
    seen: list = []

    def decide(sentence):
        seen.append(sentence)
        return {"action": "volume", "args": {"op": "get"}}

    r1 = harness_loop.run_once(words("volume", "up"), decide_fn=decide)
    r2 = harness_loop.run_once(words("volume", "down"), decide_fn=decide)
    assert r1 is not None and r2 is not None
    assert seen == ["volume up", "volume down"], seen
    assert harness_loop.pending_words() == []
