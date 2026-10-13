"""Kyuma supervisor — Phase 15.

One terminal command boots everything::

    .venv/bin/python harness/supervisor.py start      # foreground, Ctrl-C stops
    .venv/bin/python harness/supervisor.py stop       # SIGINT supervisor, reap leftovers
    .venv/bin/python harness/supervisor.py status     # children alive?

Spawns in order: model-server wrapper, then the harness loop
(``harness/loop.py:main()`` — Phase 14 sibling must provide this entry; the
loop owns STT → buffer → decide → executor and MUST write the state file
below at startup and on every dispatch). Optional ``start --ui`` also spawns
the QuickShell overlay (``quickshell -p ui/shell.qml``).

State sharing: the loop writes ``$KYUMA_STATE_FILE`` (default
``/tmp/kyuma-state.json``) as ``{listening, last_sentence, last_action,
result, ts}``. The supervisor treats a fresh write (mtime >= spawn time) as
the loop health signal; the QML overlay polls the same file every 500ms.

Stdlib only. Each child runs in its own process group (``start_new_session``)
so shutdown kills the whole group — no orphans on the SIGINT path. Dead
children are restarted up to 3 times each, then the supervisor errors out.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATE_FILE = os.environ.get("KYUMA_STATE_FILE", "/tmp/kyuma-state.json")
PID_FILE = os.environ.get("KYUMA_PID_FILE", "/tmp/kyuma-supervisor.pid")
STATUS_FILE = os.environ.get("KYUMA_STATUS_FILE", "/tmp/kyuma-supervisor.json")
MODEL_PORT = int(os.environ.get("KYUMA_MODEL_PORT", "8080"))
BOOT_TIMEOUT = float(os.environ.get("KYUMA_BOOT_TIMEOUT", "180"))
POLL = float(os.environ.get("KYUMA_POLL", "0.5"))
MAX_RESTARTS = 3
STOP_WAIT = 10.0

STOP = threading.Event()


def log(msg: str) -> None:
    print(f"[supervisor] {msg}", flush=True)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False
    # An exited-but-unreaped child (zombie) still answers kill(pid, 0);
    # treat it as gone. /proc absent (non-Linux) -> keep old behavior.
    try:
        with open(f"/proc/{pid}/stat") as f:
            state = f.read().rsplit(")", 1)[1].split()[0]
        if state == "Z":
            return False
    except (OSError, IndexError):
        pass
    return True


def _kill_tree(pid: int, sig: int) -> None:
    """Signal the child's process group (== pid, via start_new_session)."""
    try:
        os.killpg(pid, sig)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            os.kill(pid, sig)
        except (ProcessLookupError, PermissionError, OSError):
            pass


def _model_healthy() -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{MODEL_PORT}/health", timeout=3
        ) as r:
            return r.status == 200
    except Exception:
        return False


def _loop_healthy(since: float) -> bool:
    """Loop is healthy once it writes a fresh state file (mtime >= spawn)."""
    try:
        if os.stat(STATE_FILE).st_mtime < since:
            return False
        with open(STATE_FILE) as f:
            obj = json.load(f)
        return isinstance(obj, dict) and "listening" in obj
    except (OSError, ValueError):
        return False


def _model_cmd() -> list[str]:
    override = os.environ.get("KYUMA_MODEL_CMD")
    if override:
        return shlex.split(override)
    return [sys.executable, os.path.join(REPO, "model-server", "server.py"),
            "--port", str(MODEL_PORT)]


def _loop_cmd() -> list[str]:
    override = os.environ.get("KYUMA_LOOP_CMD")
    if override:
        return shlex.split(override)
    return [sys.executable, os.path.join(REPO, "harness", "loop.py")]


def _ui_cmd() -> list[str] | None:
    override = os.environ.get("KYUMA_UI_CMD")
    if override:
        return shlex.split(override)
    qs = shutil.which("quickshell")
    if not qs:
        return None
    return [qs, "-p", os.path.join(REPO, "ui", "shell.qml")]


class Child:
    def __init__(self, name: str, cmd: list[str], healthy) -> None:
        self.name = name
        self.cmd = cmd
        self.healthy = healthy  # () -> bool; loop child uses spawn-bound time
        self.proc: subprocess.Popen | None = None
        self.restarts = 0
        self.spawn_time = 0.0


class Supervisor:
    def __init__(self, with_ui: bool) -> None:
        self.ready = False
        self.children = [
            Child("model-server", _model_cmd(), _model_healthy),
            Child("harness-loop", _loop_cmd(),
                  lambda: _loop_healthy(self.by_name("harness-loop").spawn_time)),
        ]
        if with_ui:
            cmd = _ui_cmd()
            if cmd is None:
                log("quickshell binary not found, skipping UI child")
            else:
                # UI has no health endpoint; alive == healthy.
                self.children.append(Child("quickshell-ui", cmd, lambda: True))

    def by_name(self, name: str) -> Child:
        for c in self.children:
            if c.name == name:
                return c
        raise KeyError(name)

    def write_status(self) -> None:
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump({
                    "supervisor": os.getpid(),
                    "children": {c.name: c.proc.pid for c in self.children
                                 if c.proc is not None},
                    "ready": self.ready,
                    "ts": time.time(),
                }, f)
        except OSError as e:
            log(f"status write failed: {e}")

    def spawn(self, child: Child) -> None:
        log(f"spawning {child.name}: {' '.join(child.cmd)}")
        child.proc = subprocess.Popen(child.cmd, start_new_session=True)
        child.spawn_time = time.time()
        self.write_status()

    def wait_healthy(self, child: Child, timeout: float) -> bool:
        t0 = time.time()
        while time.time() - t0 < timeout and not STOP.is_set():
            assert child.proc is not None
            if child.proc.poll() is not None:
                log(f"{child.name} exited during boot (code {child.proc.returncode})")
                return False
            if child.healthy():
                log(f"{child.name} healthy")
                return True
            STOP.wait(0.5)
        if not STOP.is_set():
            log(f"{child.name} not healthy within {timeout:.0f}s")
        return False

    def shutdown(self) -> None:
        for child in reversed(self.children):
            proc = child.proc
            if proc is None or proc.poll() is not None:
                continue
            log(f"stopping {child.name} (pid {proc.pid})")
            _kill_tree(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=STOP_WAIT)
            except subprocess.TimeoutExpired:
                log(f"{child.name} ignoring SIGTERM, SIGKILL")
                _kill_tree(proc.pid, signal.SIGKILL)
                proc.wait()
        for path in (PID_FILE, STATUS_FILE):
            try:
                os.unlink(path)
            except OSError:
                pass

    def run(self) -> int:
        for child in self.children:
            if STOP.is_set():
                log("interrupted before boot, shutting down")
                self.shutdown()
                return 0
            self.spawn(child)
            if not self.wait_healthy(child, BOOT_TIMEOUT):
                if STOP.is_set():
                    log("interrupted during boot, shutting down")
                    self.shutdown()
                    return 0
                log("boot failed, shutting down")
                self.shutdown()
                return 1
        self.ready = True
        self.write_status()
        log("all services healthy")
        while not STOP.is_set():
            for child in self.children:
                proc = child.proc
                assert proc is not None
                if proc.poll() is None:
                    continue
                proc.wait()  # reap zombie
                if child.restarts >= MAX_RESTARTS:
                    log(f"ERROR: {child.name} died {MAX_RESTARTS}x, "
                        f"restart budget exhausted")
                    self.shutdown()
                    return 1
                child.restarts += 1
                log(f"{child.name} died (code {proc.returncode}), "
                    f"restart {child.restarts}/{MAX_RESTARTS}")
                self.spawn(child)
                if not self.wait_healthy(child, BOOT_TIMEOUT):
                    log(f"ERROR: {child.name} did not recover, shutting down")
                    self.shutdown()
                    return 1
            STOP.wait(POLL)
        log("SIGINT, shutting down")
        self.shutdown()
        return 0


def _read_pid() -> int | None:
    try:
        with open(PID_FILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def cmd_start(with_ui: bool) -> int:
    pid = _read_pid()
    if pid is not None and _alive(pid):
        print(f"supervisor already running (pid {pid})", flush=True)
        return 1
    for stale in (PID_FILE, STATUS_FILE):
        try:
            os.unlink(stale)
        except OSError:
            pass
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    def _on_signal(signum, _frame) -> None:
        STOP.set()

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)
    log(f"starting (pid {os.getpid()}, state {STATE_FILE})")
    try:
        return Supervisor(with_ui).run()
    finally:
        try:
            os.unlink(PID_FILE)
        except OSError:
            pass


def _sweep_status_pids() -> None:
    """Reap leftover children from the status file (covers supervisor crash)."""
    try:
        with open(STATUS_FILE) as f:
            status = json.load(f)
    except (OSError, ValueError):
        return
    children = status.get("children", {})
    if not isinstance(children, dict):
        return
    for name, pid in children.items():
        if not isinstance(pid, int) or not _alive(pid):
            continue
        log(f"sweeping leftover {name} (pid {pid})")
        _kill_tree(pid, signal.SIGTERM)
        t0 = time.time()
        while _alive(pid) and time.time() - t0 < STOP_WAIT:
            time.sleep(0.2)
        if _alive(pid):
            _kill_tree(pid, signal.SIGKILL)


def _sweep_markers() -> None:
    """Kill leftover Kyuma children by process marker (covers Ctrl-C orphaning).

    The supervisor puts children in their own process groups, so a terminal
    Ctrl-C kills only the supervisor and orphans the tree. Markers match only
    OUR processes: never the sibling :8081 server, never test stubs.
    """
    import subprocess as _sp
    markers = ("harness/loop.py", "model-server/server.py", "quickshell -p")
    try:
        out = _sp.run(["pgrep", "-f", "|".join(f"({m})" for m in markers)],
                      capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001
        return
    me = os.getpid()
    for line in out.splitlines():
        try:
            pid = int(line.strip())
        except ValueError:
            continue
        if pid == me or not _alive(pid):
            continue
        cmd = ""
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if "pytest" in cmd or "gate.sh" in cmd or "conftest" in cmd:
            continue  # never kill the test harness
        if "quickshell -p" in cmd and "ui/shell.qml" not in cmd:
            continue  # only our overlay, never Caelestia or other shells
        log(f"sweeping leftover process (pid {pid}): {cmd[:120]}")
        _kill_tree(pid, signal.SIGTERM)
    time.sleep(1.0)


def cmd_stop() -> int:
    pid = _read_pid()
    if pid is None:
        print("supervisor not running (no pidfile)", flush=True)
        _sweep_status_pids()
        _sweep_markers()
        return 1
    if _alive(pid):
        log(f"SIGINT supervisor (pid {pid})")
        try:
            os.kill(pid, signal.SIGINT)
        except OSError:
            pass
        t0 = time.time()
        while _alive(pid) and time.time() - t0 < 30:
            time.sleep(0.2)
    _sweep_status_pids()  # no orphans even if the supervisor had crashed
    _sweep_markers()  # Ctrl-C orphans have no status entry; kill by marker
    for path in (PID_FILE, STATUS_FILE):
        try:
            os.unlink(path)
        except OSError:
            pass
    if pid is not None and _alive(pid):
        print(f"supervisor pid {pid} still alive", flush=True)
        return 1
    print("stopped", flush=True)
    return 0


def cmd_status() -> int:
    pid = _read_pid()
    if pid is None or not _alive(pid):
        print("supervisor: not running", flush=True)
        return 1
    print(f"supervisor: running (pid {pid})", flush=True)
    ok = True
    try:
        with open(STATUS_FILE) as f:
            status = json.load(f)
        children = status.get("children", {})
    except (OSError, ValueError):
        children = {}
    if not children:
        print("children: unknown (no status file)", flush=True)
        return 1
    for name, cpid in children.items():
        alive = isinstance(cpid, int) and _alive(cpid)
        ok = ok and alive
        print(f"  {name}: {'alive (pid %d)' % cpid if alive else 'DEAD'}",
              flush=True)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Kyuma supervisor (Phase 15)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_start = sub.add_parser("start", help="boot model-server + harness loop")
    p_start.add_argument("--no-ui", action="store_true",
                         help="skip the QuickShell overlay (default: spawn it)")
    sub.add_parser("stop", help="SIGINT supervisor, reap leftover children")
    sub.add_parser("status", help="report supervisor + children liveness")
    args = ap.parse_args(argv)
    if args.cmd == "start":
        return cmd_start(not args.no_ui)
    if args.cmd == "stop":
        return cmd_stop()
    return cmd_status()


if __name__ == "__main__":
    sys.exit(main())
