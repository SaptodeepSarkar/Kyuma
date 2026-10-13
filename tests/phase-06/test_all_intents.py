"""Binding gate: every fixture sentence -> correct action (target >=95%)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "model-server"))

from fixtures import CASES, decide_on  # noqa: E402


def test_all_intents(server):
    model = os.environ.get("DECIDE_MODEL", "?")
    hits, misses = 0, []
    for sentence, expected in CASES:
        got = decide_on(server, sentence).get("action")
        if got == expected:
            hits += 1
        else:
            misses.append((sentence, expected, got))
    acc = hits / len(CASES)
    print(f"\n[{model}] accuracy: {hits}/{len(CASES)} = {acc:.1%}")
    for s, e, g in misses:
        print(f"  MISS {s!r}: want {e}, got {g}")
    assert acc >= 0.95, f"accuracy {acc:.1%} < 95% ({len(misses)} misses)"
