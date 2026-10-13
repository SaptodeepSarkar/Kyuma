"""Flush on error: a failing command leaves no words behind."""
from harness import loop as harness_loop


def test_error_flushes_and_next_command_works(words):
    seen: list = []

    def decide(sentence):
        seen.append(sentence)
        if len(seen) == 1:
            return {"action": "open_app", "args": {"name": "no-such-app-xyz"}}
        return {"action": "volume", "args": {"op": "get"}}

    log: list = []
    res = harness_loop.run_once(words("open", "no-such-app-xyz"), decide_fn=decide, log=log)
    assert res is not None and res.code == "error", res
    assert harness_loop.pending_words() == [], "buffer must be empty after error"
    res2 = harness_loop.run_once(words("volume", "up"), decide_fn=decide, log=log)
    assert res2 is not None  # routed and answered; code may be error without audio
    assert seen == ["open no-such-app-xyz", "volume up"], seen


def test_decide_exception_flushes(words):
    def boom(sentence):
        raise RuntimeError("model exploded")

    res = harness_loop.run_once(words("volume", "up"), decide_fn=boom)
    assert res is not None and res.code == "error", res
    assert "model exploded" in res.detail
    assert harness_loop.pending_words() == []
