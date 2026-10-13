"""Phase-14 gates: real handlers, buffer isolation, audio snapshot, model server.

Model server: reuse the wrapper on 127.0.0.1:8081 when it answers with the
wrapper ``/health`` shape (``{"loaded": ...}``); else spawn the wrapper on an
ephemeral port via the phase-05 helper; else yield None and the tests use a
deterministic stub decide (a responding raw llama-server is NOT the wrapper
API, and a second model copy in VRAM is not worth it for scripted gates).
"""
from __future__ import annotations

import importlib.util
import json
import os
import urllib.request

import pytest

import executor
from harness import loop as harness_loop
from helpers import make_words, parse_volume, wpctl

executor.register_all()

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PHASE05_CONFTEST = os.path.join(REPO, "tests", "phase-05", "conftest.py")
WRAPPER = "http://127.0.0.1:8081"


def _get_json(url: str, timeout: float = 3.0) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


def _wrapper_up() -> bool:
    body = _get_json(WRAPPER + "/health")
    return isinstance(body, dict) and bool(body.get("loaded"))


def _load_phase05():
    spec = importlib.util.spec_from_file_location("phase05_conftest", PHASE05_CONFTEST)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _fresh_buffer():
    harness_loop.reset_buffer()
    yield
    harness_loop.reset_buffer()


@pytest.fixture
def words():
    return make_words


@pytest.fixture
def audio_state():
    """Skip without an audio stack; else snapshot volume/mute, restore after."""
    try:
        level, muted = parse_volume(wpctl("get-volume", "@DEFAULT_AUDIO_SINK@"))
    except Exception as e:  # noqa: BLE001 -- missing stack skips, never fails
        pytest.skip(f"audio stack required: {e}")
    yield {"level": level, "muted": muted}
    try:
        wpctl("set-volume", "@DEFAULT_AUDIO_SINK@", f"{level / 100:.4f}")
        wpctl("set-mute", "@DEFAULT_AUDIO_SINK@", "1" if muted else "0")
        got, got_muted = parse_volume(wpctl("get-volume", "@DEFAULT_AUDIO_SINK@"))
        if (got, got_muted) != (level, muted):  # transient mixer miss: one retry
            wpctl("set-volume", "@DEFAULT_AUDIO_SINK@", f"{level / 100:.4f}")
            wpctl("set-mute", "@DEFAULT_AUDIO_SINK@", "1" if muted else "0")
    except Exception as e:  # noqa: BLE001 -- restore must not fail the gate
        print(f"\nWARNING: audio restore failed: {e}")


@pytest.fixture(scope="session")
def model_server():
    """Live wrapper URL, or None (tests fall back to a stub decide)."""
    if _wrapper_up():
        yield WRAPPER
        return
    try:
        helper = _load_phase05()
        proc, base = helper.spawn()
    except Exception as e:  # noqa: BLE001 -- no backend here: stub path
        print(f"\nNOTE: no live model server ({e}); using stub decide")
        yield None
        return
    try:
        yield base
    finally:
        helper.stop(proc)
