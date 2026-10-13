"""Gate: empty sentence -> 4xx, no crash, server stays up."""
from conftest import _get, _post


def test_bad_input(server):
    for bad in ({"sentence": ""}, {"sentence": "   "}, {}, {"sentence": 42}):
        code, _ = _post(server, "/decide", bad)
        assert 400 <= code < 500, bad

    code, _ = _post(server, "/decide", None, raw=b"{not json")
    assert 400 <= code < 500

    # Server stays up: health OK and a good call still answers.
    assert _get(server, "/health")[0] == 200
    code, exec_ = _post(server, "/decide", {"sentence": "open firefox"})
    assert code == 200, exec_
