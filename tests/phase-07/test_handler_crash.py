"""Handler crash -> error Result, dispatcher stays alive."""
import executor.dispatch as d
from executor.dispatch import dispatch
from harness.contracts import Exec, Result


def test_handler_crash():
    old = d.HANDLERS["volume"]

    def boom(args):
        raise RuntimeError("speaker exploded")

    d.HANDLERS["volume"] = boom
    try:
        res = dispatch(Exec(action="volume", args={}))
        assert res.code == "error"
        assert "volume" in res.detail
    finally:
        d.HANDLERS["volume"] = old
    # dispatcher stays alive
    assert dispatch(Exec(action="volume", args={})).code == 200


def test_bad_return_type_is_error():
    old = d.HANDLERS["music"]
    d.HANDLERS["music"] = lambda args: "not-a-result"
    try:
        assert dispatch(Exec(action="music", args={})).code == "error"
    finally:
        d.HANDLERS["music"] = old
    assert isinstance(dispatch(Exec(action="music", args={})), Result)
