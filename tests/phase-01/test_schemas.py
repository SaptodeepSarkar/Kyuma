"""Phase 01 gate: frozen schemas accept valid samples, reject invalid ones."""
import pytest

from harness.contracts import ACTIONS, Exec, Result, Word


def test_word_valid():
    w = Word(w="hello", t=1.25)
    assert w.w == "hello" and w.t == 1.25
    assert Word.from_dict({"w": "hi", "t": 0}) == Word(w="hi", t=0.0)


@pytest.mark.parametrize("bad", [
    {"w": "", "t": 1.0},        # empty text
    {"w": "hi", "t": -1.0},     # negative timestamp
    {"w": 42, "t": 1.0},        # non-str text
    {"w": "hi"},                # missing t
    {"t": 1.0},                 # missing w
    "not-a-dict",
])
def test_word_invalid(bad):
    with pytest.raises((ValueError, TypeError)):
        Word.from_dict(bad)


def test_exec_valid_all_actions():
    for action in ACTIONS:
        e = Exec(action=action, args={})
        assert Exec.from_dict({"action": action, "args": {"k": "v"}}).action == action
    assert len(ACTIONS) == 10  # closed list mirrors the 10 capabilities


@pytest.mark.parametrize("bad", [
    {"action": "delete_system32", "args": {}},  # unknown action
    {"action": "", "args": {}},                # empty action
    {"action": "volume", "args": ["loud"]},    # args not a dict
    {"action": "volume"},                      # missing args
    {"args": {}},                              # missing action
])
def test_exec_invalid(bad):
    with pytest.raises((ValueError, TypeError)):
        Exec.from_dict(bad)


def test_result_valid():
    assert Result(code=200, detail="ok").code == 200
    assert Result.from_dict({"code": "error", "detail": "boom"}).code == "error"


@pytest.mark.parametrize("bad", [
    {"code": 404, "detail": "x"},   # only 200 or "error"
    {"code": 200, "detail": 123},   # detail must be str
    {"code": 200},                  # missing detail
])
def test_result_invalid(bad):
    with pytest.raises((ValueError, TypeError)):
        Result.from_dict(bad)
