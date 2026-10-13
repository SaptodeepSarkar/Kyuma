"""Phase 06 conftest: live llama-server location (own instance on 8081)."""
import os
import urllib.request

import pytest

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
        pytest.skip(f"no llama-server at {SERVER} (start one for the bake-off)")
    return SERVER
