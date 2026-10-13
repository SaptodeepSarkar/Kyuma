"""Phase 01 gate: harness -> executor round-trip returns a valid Result.

Stub ends: no HTTP server yet — the "wire" is JSON encode/decode and the
executor is an in-process stub. Phase 07 replaces the stub with real dispatch.
"""
import json

from harness.contracts import Exec, Result


def fake_executor(payload_json: str) -> str:
    """Stand-in for the executor end of the HTTP/JSON IPC."""
    req = Exec.from_dict(json.loads(payload_json))
    if req.action == "volume":
        return json.dumps(Result(code=200, detail="volume ok").to_dict())
    return json.dumps(Result(code="error", detail=f"stub: no capability {req.action}").to_dict())


def round_trip(exec_msg: Exec) -> Result:
    wire_out = json.dumps(exec_msg.to_dict())  # harness -> wire
    wire_back = fake_executor(wire_out)        # executor -> wire
    return Result.from_dict(json.loads(wire_back))


def test_ipc_ping_success():
    res = round_trip(Exec(action="volume", args={"level": 50}))
    assert res.code == 200


def test_ipc_ping_error_still_returns_result():
    res = round_trip(Exec(action="music", args={"op": "next"}))
    assert res.code == "error" and isinstance(res.detail, str)
