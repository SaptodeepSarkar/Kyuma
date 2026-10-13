"""Boot order: model-server spawned + healthy BEFORE the harness loop."""
import signal

from conftest import _status, _teardown


def test_boot_order(started):
    proc, env = started
    # Order + health asserted via status file and log lines below.
    st = _status(env)
    assert {"model-server", "harness-loop"} <= set(st["children"])  # ui stub allowed
    # Clean stop; then inspect the full captured log for spawn order.
    proc.send_signal(signal.SIGINT)
    rest = proc.stdout.read()
    proc.wait(timeout=30)
    assert proc.returncode == 0
    log = rest
    i_spawn_m = log.find("spawning model-server")
    i_healthy_m = log.find("model-server healthy")
    i_spawn_l = log.find("spawning harness-loop")
    i_healthy_l = log.find("harness-loop healthy")
    assert -1 not in (i_spawn_m, i_healthy_m, i_spawn_l, i_healthy_l), log
    assert i_spawn_m < i_healthy_m < i_spawn_l < i_healthy_l, log
    assert "all services healthy" in log
    proc.stdout.close()
    # Prevent fixture teardown from double-stopping (already exited).
