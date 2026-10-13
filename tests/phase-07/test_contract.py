"""Every dispatch response matches the Phase 01 Result schema."""
import json

from executor.dispatch import dispatch
from harness.contracts import ACTIONS, Exec, Result


def test_contract():
    cases = [Exec(action=a, args={}) for a in ACTIONS]
    cases += ["garbage", {"action": "nope", "args": {}}]
    for c in cases:
        res = dispatch(c)
        assert isinstance(res, Result)
        assert res.code == 200 or res.code == "error"
        assert isinstance(res.detail, str)
        back = Result.from_dict(json.loads(json.dumps(res.to_dict())))
        assert back == res
