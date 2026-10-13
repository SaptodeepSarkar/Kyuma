"""Malformed Exec -> error Result, no exception."""
import pytest

from executor.dispatch import dispatch


@pytest.mark.parametrize("bad", [
    {"action": "delete_system32", "args": {}},
    {"action": "", "args": {}},
    {"action": "volume"},                       # missing args
    {"args": {}},                               # missing action
    {"action": "volume", "args": ["loud"]},     # args not a dict
    {"action": "volume", "args": None},
    "not-a-dict",
    None,
    42,
])
def test_invalid(bad):
    res = dispatch(bad)  # must not raise
    assert res.code == "error"
    assert isinstance(res.detail, str) and res.detail
