"""Phase 15 shared fixtures: stub model/loop children + supervisor runner.

Real model-server takes minutes to load; the gate uses stub children via
KYUMA_MODEL_CMD / KYUMA_LOOP_CMD overrides. The supervisor only requires:
model child serves GET /health -> 200, loop child writes a fresh state file
{listening, ...} — the same contract the real Phase 14 loop must honor.
"""
import json
import os
import signal
import socket
import subprocess
import sys
import time

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SUPERVISOR = os.path.join(REPO, "harness", "supervisor.py")

MODEL_STUB = """\
import http.server, json, sys
port = int(sys.argv[1])
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"loaded": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", port), H).serve_forever()
"""

LOOP_STUB = """\
import json, signal, sys, time
state = sys.argv[1]
signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
with open(state, "w") as f:  # fresh write == loop-healthy (mtime >= spawn)
    json.dump({"listening": True, "last_sentence": "volume up",
               "last_action": "volume",
               "result": {"code": 200, "detail": "ok"},
               "ts": time.time()}, f)
while True:
    time.sleep(1)
"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_until(fn, timeout: float = 20.0, interval: float = 0.1):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if fn():
            return True
        time.sleep(interval)
    return False


@pytest.fixture
def env(tmp_path):
    """Isolated pid/status/state files, stub children, fast timeouts."""
    state = tmp_path / "state.json"
    port = free_port()
    model_stub = tmp_path / "model_stub.py"
    loop_stub = tmp_path / "loop_stub.py"
    model_stub.write_text(MODEL_STUB)
    loop_stub.write_text(LOOP_STUB)
    e = dict(os.environ)
    e.update({
        "KYUMA_STATE_FILE": str(state),
        "KYUMA_PID_FILE": str(tmp_path / "supervisor.pid"),
        "KYUMA_STATUS_FILE": str(tmp_path / "supervisor.json"),
        "KYUMA_MODEL_PORT": str(port),
        "KYUMA_MODEL_CMD": f"{sys.executable} {model_stub} {port}",
        "KYUMA_LOOP_CMD": f"{sys.executable} {loop_stub} {state}",
        "KYUMA_UI_CMD": "sleep 60",  # ui stub (always-healthy child)
        "KYUMA_BOOT_TIMEOUT": "15",
        "KYUMA_POLL": "0.1",
        "PYTHONUNBUFFERED": "1",
    })
    e["supervisor_py"] = SUPERVISOR
    e["tmpdir"] = str(tmp_path)
    return e


@pytest.fixture
def started(env):
    """Supervisor started with stubs; SIGINT + reaped on teardown."""
    proc = subprocess.Popen(
        [sys.executable, "-u", SUPERVISOR, "start"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    assert wait_until(
        lambda: _both_healthy(env), timeout=25), "supervisor did not boot"
    yield proc, env
    _teardown(proc, env)


def _status(env) -> dict:
    try:
        with open(env["KYUMA_STATUS_FILE"]) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _both_healthy(env) -> bool:
    st = _status(env)
    kids = st.get("children", {})
    if not {"model-server", "harness-loop"} <= set(kids):
        return False  # ui stub child allowed alongside (default-on UI)
    if st.get("ready") is not True:  # supervisor finished booting
        return False
    try:
        with open(env["KYUMA_STATE_FILE"]) as f:
            obj = json.load(f)
        return isinstance(obj, dict) and obj.get("listening") is True
    except (OSError, ValueError):
        return False


def _teardown(proc, env) -> None:
    if proc.poll() is None:
        try:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    try:
        proc.stdout.close()
    except Exception:
        pass
    # No orphans may survive the fixture.
    for pid in _status(env).get("children", {}).values():
        try:
            os.kill(pid, 0)
        except OSError:
            continue
        raise AssertionError(f"orphan child survived: pid {pid}")
