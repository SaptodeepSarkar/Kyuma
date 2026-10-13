"""Gate: /health reports loaded flag + device truthfully."""
from conftest import _get


def test_health(server):
    code, body = _get(server, "/health")
    assert code == 200, body
    assert body["loaded"] is True
    assert body["device"] in ("cuda", "cpu")
    assert body["backend"] == "llama-server"
    assert isinstance(body["model"], str) and body["model"].endswith(".gguf")
    # vram_mb is an int when nvidia-smi exists, else None — either is truthful.
    assert body["vram_mb"] is None or isinstance(body["vram_mb"], int)
