"""Spawn model-server/server.py as a subprocess for gate tests (stdlib only)."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVER = os.path.join(REPO, "model-server", "server.py")
PY = sys.executable
assert os.path.isfile(SERVER), f"wrapper not found: {SERVER}"


def _get(base: str, path: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(base + path, timeout=30) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:  # noqa: F841
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


def _post(base: str, path: str, obj: object, raw: bytes | None = None) -> tuple[int, dict]:
    data = raw if raw is not None else json.dumps(obj).encode()
    req = urllib.request.Request(base + path, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


def spawn(extra_args: list[str] | None = None) -> tuple[subprocess.Popen, str]:
    proc = subprocess.Popen(
        [PY, SERVER, "--port", "0"] + (extra_args or []),
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1,
        start_new_session=True,  # own process group: teardown can reap orphans
    )
    line = proc.stdout.readline()  # {"listening": port, ...} once backend is ready
    info = json.loads(line)
    base = f"http://127.0.0.1:{info['listening']}"
    for _ in range(60):  # wrapper binds only after backend ready; still, poll
        try:
            code, body = _get(base, "/health")
            if code == 200 and body.get("loaded"):
                return proc, base
        except Exception:
            pass
        time.sleep(2.0)
    proc.terminate()
    raise TimeoutError("model-server did not become ready")


def stop(proc: subprocess.Popen) -> None:
    """SIGTERM the wrapper (it reaps its backend); SIGKILL the group if stuck."""
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        pass
    try:  # wrapper gone but backend orphaned, or wrapper stuck: reap the group
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="module")
def server():
    proc, base = spawn()
    yield base
    stop(proc)
