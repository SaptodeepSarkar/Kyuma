"""UI state: after a loop run the state object carries the sentence +
result, and shell.qml binds every key (headless assert; QML launch is
verified manually on Hyprland, not in the gate).
"""
import json
import os
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QML = os.path.join(REPO, "ui", "shell.qml")

STATE_KEYS = ("listening", "last_sentence", "last_action", "result", "ts")
QML_KEYS = ("listening", "last_sentence", "last_action", "result")


def test_ui_state(started):
    proc, env = started
    # Simulate a loop run: fresh state write, as harness/loop.py:main() must.
    with open(env["KYUMA_STATE_FILE"]) as f:
        state = json.load(f)
    for key in STATE_KEYS:
        assert key in state, f"state object missing {key!r}: {state}"
    assert state["listening"] is True
    assert isinstance(state["last_sentence"], str) and state["last_sentence"]
    assert isinstance(state["last_action"], str) and state["last_action"]
    assert isinstance(state["ts"], (int, float))
    assert time.time() - state["ts"] < 60

    with open(QML) as f:
        qml = f.read()
    for key in QML_KEYS:
        assert key in qml, f"shell.qml does not bind state key {key!r}"
    assert "ShellRoot" in qml and "PanelWindow" in qml
    assert "interval: 500" in qml, "overlay must poll every 500ms"
