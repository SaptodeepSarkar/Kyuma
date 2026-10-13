"""Gate: forced CPU/offload config still answers (slower allowed)."""
from harness.contracts import ACTIONS

from conftest import _get, _post, spawn, stop


def test_offload():
    proc, base = spawn(["--device", "cpu"])
    try:
        code, body = _get(base, "/health")
        assert code == 200 and body["loaded"] is True
        assert body["device"] == "cpu"

        code, exec_ = _post(base, "/decide", {"sentence": "pause the music"})
        assert code == 200, exec_
        assert exec_["action"] in ACTIONS and isinstance(exec_["args"], dict)
    finally:
        stop(proc)
