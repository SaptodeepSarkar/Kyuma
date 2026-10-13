"""Phase 16 shared fixtures: live decide server + hermetic (stubbed) dispatch."""
import os
import sys
import urllib.request

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "model-server"))
sys.path.insert(0, os.path.join(REPO, "tests", "phase-06"))

SERVER = os.environ.get("DECIDE_URL", "http://localhost:8081")


def _up() -> bool:
    try:
        with urllib.request.urlopen(SERVER.rstrip("/") + "/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def server() -> str:
    if not _up():
        pytest.skip(f"no decide server at {SERVER} (start model-server for Phase 16)")
    return SERVER


@pytest.fixture
def hermetic_dispatch():
    """Swap every dispatch handler for a 200 stub (no side effects), restore after."""
    import executor.dispatch as d
    from harness.contracts import Result
    saved = dict(d.HANDLERS)
    for action in saved:
        def stub(args, _a=action):
            return Result(code=200, detail=f"{_a} stub ok")
        d.HANDLERS[action] = stub
    try:
        yield d
    finally:
        d.HANDLERS.clear()
        d.HANDLERS.update(saved)
