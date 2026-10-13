"""Gate: model stays resident — two /decide calls, no reload between."""
from harness.contracts import ACTIONS

from conftest import _get, _post


def test_resident(server):
    before = _get(server, "/health")[1]
    assert before["loaded"] is True

    code1, exec1 = _post(server, "/decide", {"sentence": "switch to workspace three"})
    assert code1 == 200, exec1
    assert exec1["action"] in ACTIONS and isinstance(exec1["args"], dict)

    code2, exec2 = _post(server, "/decide", {"sentence": "open firefox"})
    assert code2 == 200, exec2
    assert exec2["action"] in ACTIONS and isinstance(exec2["args"], dict)

    after = _get(server, "/health")[1]
    assert after["loaded"] is True
    # Same process served both: counter advanced by exactly 2, no reset.
    assert after["decides"] == before["decides"] + 2
