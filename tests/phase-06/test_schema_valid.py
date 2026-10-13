"""Gate: 100% of in-scope outputs parse as Exec (grammar guarantees syntax)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "model-server"))

import decide_prompt  # noqa: E402
from decide_prompt import validate_exec
from fixtures import decide_on  # noqa: E402
from fixtures import CASES  # noqa: E402


def test_schema_valid(server):
    bad = []
    for sentence, _ in CASES:
        try:
            validate_exec(decide_on(server, sentence))
        except ValueError as e:
            bad.append((sentence, str(e)))
    for s, e in bad:
        print(f"  SCHEMA-FAIL {s!r}: {e}")
    assert not bad, f"{len(bad)}/{len(CASES)} outputs failed Exec validation"
