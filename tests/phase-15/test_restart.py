"""Kill a child -> supervisor restarts it, healthy again."""
import json
import os
import signal
import time

from conftest import _status, wait_until


def test_restart(started):
    proc, env = started
    old_pid = _status(env)["children"]["harness-loop"]
    os.kill(old_pid, signal.SIGKILL)

    def _recovered():
        st = _status(env)
        new_pid = st.get("children", {}).get("harness-loop")
        if not new_pid or new_pid == old_pid:
            return False
        try:
            with open(env["KYUMA_STATE_FILE"]) as f:
                obj = json.load(f)
            return obj.get("listening") is True
        except (OSError, ValueError):
            return False

    assert wait_until(_recovered, timeout=25), "loop child did not recover"
    new_pid = _status(env)["children"]["harness-loop"]
    assert new_pid != old_pid
    try:
        os.kill(old_pid, 0)
        raise AssertionError(f"killed pid {old_pid} still alive")
    except OSError:
        pass  # expected: old child is gone
    assert proc.poll() is None  # supervisor itself survived
    assert time.time() - os.stat(env["KYUMA_STATE_FILE"]).st_mtime < 30
