"""Gate: non-command speech -> safe noop, never a wild action (FAR target 0)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "model-server"))

from decide_prompt import validate_exec
from fixtures import decide_on  # noqa: E402
from fixtures import GIBBERISH  # noqa: E402


def test_gibberish(server):
    fired = []
    for sentence in GIBBERISH:
        try:
            exe = validate_exec(decide_on(server, sentence))
            fired.append((sentence, exe.action, exe.args))
        except ValueError:
            pass  # safe noop — the desired outcome
    for s, a, args in fired:
        print(f"  FALSE-ACCEPT {s!r} -> {a} {args}")
    far = len(fired) / len(GIBBERISH)
    print(f"\nFAR: {len(fired)}/{len(GIBBERISH)} = {far:.1%}")
    assert not fired, f"FAR {far:.1%}: gibberish triggered real actions"
