"""SIGINT -> all children exit, pidfile gone, no orphan PIDs."""
import os
import subprocess
import sys

from conftest import SUPERVISOR, _status, wait_until


def test_clean_shutdown(started):
    proc, env = started
    pids = dict(_status(env)["children"])
    assert {"model-server", "harness-loop"} <= set(pids)  # ui stub allowed + reaped below
    # Exercise the real `stop` CLI (SIGINT + leftover sweep), not a raw signal.
    r = subprocess.run([sys.executable, SUPERVISOR, "stop"],
                       env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert proc.wait(timeout=30) == 0
    proc.stdout.close()
    for name, pid in pids.items():
        try:
            os.kill(pid, 0)
        except OSError:
            continue
        raise AssertionError(f"orphan survived: {name} pid {pid}")
    assert not os.path.exists(env["KYUMA_PID_FILE"])
    assert wait_until(lambda: proc.poll() is not None, timeout=5)
