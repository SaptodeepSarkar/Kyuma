"""Gate: scripted soak — fixture commands + silence + gibberish, zero crashes."""
import time

from fixtures import CASES, GIBBERISH, decide_on  # noqa: E402 (path set in conftest)

from executor.dispatch import dispatch  # noqa: E402
from harness.buffer import Buffer, Word  # noqa: E402
from harness.contracts import Exec  # noqa: E402

LOOPS = 3  # accelerated: 3 x (60 commands + silence + 15 gibberish); NOT a live-mic soak


def test_soak(server, hermetic_dispatch):
    from decide_prompt import validate_exec  # noqa: E402
    buf = Buffer()
    t = 0.0
    n_ok = n_noop = n_err = crashes = 0
    wall = time.perf_counter()
    for _ in range(LOOPS):
        for sentence, _ in CASES:
            toks = sentence.split()
            toks[-1] = toks[-1] + "."  # punctuation-completeness (see buffer rule)
            emitted = []
            for w in toks:
                s = buf.feed(Word(w, t))
                t += 0.05
                if s is not None:
                    emitted.append(s)
            # Buffer may fire early at MIN_WORDS=3; joined emissions must equal
            # the sentence (no loss, no cross-sentence merge). Pending must drain.
            s = " ".join(emitted)
            assert s == sentence, f"buffer lost words: {emitted!r} vs {sentence!r}"
            assert buf.pending == [], f"stuck words after {sentence!r}: {buf.pending!r}"
            try:
                exe = validate_exec(decide_on(server, s))
            except ValueError:
                n_noop += 1  # model declined a fixture sentence; safe, keep soaking
                continue
            res = dispatch(Exec(action=exe.action, args=exe.args))
            if res.code == 200:
                n_ok += 1
            else:
                n_err += 1  # stubbed dispatch: error Results logged, loop continues
        t += 10.0  # silence gap > TIMEOUT_S: stalled fragment must discard
        buf.check_timeout(t)
        assert buf.pending == [], "stuck buffer after silence gap"
        for g in GIBBERISH:
            toks = g.split()
            toks[-1] = toks[-1] + "."  # punctuation-completeness (see buffer rule)
            emitted = []
            for w in toks:
                s = buf.feed(Word(w, t))
                t += 0.05
                if s is not None:
                    emitted.append(s)
            s = " ".join(emitted)
            if not s:  # fragment too short to complete; stall it out
                t += 10.0
                buf.check_timeout(t)
                continue
            try:
                exe = validate_exec(decide_on(server, s))
            except ValueError:
                n_noop += 1
                continue
            res = dispatch(Exec(action=exe.action, args=exe.args))
            if res.code == 200:
                n_ok += 1
            else:
                n_err += 1
    dur = time.perf_counter() - wall
    total = n_ok + n_noop + n_err
    print(f"\nsoak: {total} sentences over {dur:.0f}s wall, "
          f"ok={n_ok} noop={n_noop} dispatch-error={n_err} crashes={crashes}")
    print(f"note: accelerated scripted soak (live decide, stubbed exec); "
          f"10-min live-mic soak NOT run — no mic pipeline in this env.")
    assert crashes == 0
    assert buf.pending == [], "stuck buffer at end of soak"
