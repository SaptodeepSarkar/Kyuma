"""Gate: p95 word->action <= ~1s budget on the fixture script (live decide)."""
import statistics
import time

from fixtures import CASES, decide_on  # noqa: E402 (path set in conftest)

from executor.dispatch import dispatch  # noqa: E402 (stubs unless phases wire it)
from harness.buffer import Buffer, Word  # noqa: E402
from harness.contracts import Exec  # noqa: E402

BUDGET_MS = 1000.0


def _words(sentence: str, t0: float) -> list:
    # Terminal "." on the last word exercises the buffer's documented
    # punctuation-completeness rule (2-word commands never hit MIN_WORDS=3).
    toks = sentence.split()
    toks[-1] = toks[-1] + "."
    return [Word(w, t0 + i * 0.05) for i, w in enumerate(toks)]


def test_latency_budget(server, hermetic_dispatch):
    from decide_prompt import validate_exec  # noqa: E402
    script = [s for s, _ in CASES[::3]]  # 20 sentences strided across all 10 intents
    dts, actions = [], []
    t = 0.0
    for sentence in script:
        buf = Buffer()
        t0 = time.perf_counter()
        emitted = []
        for w in _words(sentence, t):
            out = buf.feed(w)
            if out is not None:
                emitted.append(out)
        t += len(sentence.split()) * 0.05 + 0.1
        # Buffer may fire early at MIN_WORDS=3; joined emissions must preserve
        # every word in order (no loss, no cross-sentence merge).
        out = " ".join(emitted)
        assert out == sentence, f"buffer lost words: {emitted!r} vs {sentence!r}"
        exe = validate_exec(decide_on(server, out))
        res = dispatch(Exec(action=exe.action, args=exe.args))
        assert res.code == 200, f"dispatch error for {sentence!r}: {res.detail}"
        dts.append((time.perf_counter() - t0) * 1000)
        actions.append(exe.action)
    dts.sort()
    p50 = statistics.median(dts)
    p95 = dts[min(len(dts) - 1, int(len(dts) * 0.95))]
    print(f"\nword->action: p50={p50:.0f}ms p95={p95:.0f}ms max={dts[-1]:.0f}ms n={len(dts)}")
    print(f"actions covered: {sorted(set(actions))}")
    assert p95 <= BUDGET_MS, f"p95 {p95:.0f}ms > {BUDGET_MS:.0f}ms budget"
