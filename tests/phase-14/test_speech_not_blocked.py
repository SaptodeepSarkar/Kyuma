"""Speech not blocked: words arriving during a slow decide are kept."""
import threading
import time

from harness import loop as harness_loop
from harness.contracts import Word


def test_slow_model_still_buffers(words):
    def slow(sentence):
        time.sleep(2.0)
        return {"action": "volume", "args": {"op": "get"}}

    done: list = []
    thread = threading.Thread(
        target=lambda: done.append(harness_loop.run_once(words("volume", "up"), decide_fn=slow))
    )
    thread.start()
    time.sleep(0.5)  # decide is sleeping; STT keeps streaming
    assert thread.is_alive(), "decide should still be waiting"
    assert harness_loop.ingest([Word(w="brightness", t=0.9)]) == []
    thread.join(timeout=30)
    assert not thread.is_alive()
    assert done and done[0] is not None
    pending = [(w.w, w.t) for w in harness_loop.pending_words()]
    assert pending == [("brightness", 0.9)], pending
    assert all("volume" not in w for w, _ in pending), "dispatched words must be flushed"
