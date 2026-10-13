"""Gate: ambiguous title → error Result, focus unchanged (no guessing)."""
import json
import re

from conftest import hyprctl

from executor.hyprland import handle_focus_window


def _ambiguous_title_token(clients):
    """Find a lowercase token (len>=3) present in ≥2 window titles."""
    hits = {}
    for c in clients:
        for tok in set(re.findall(r"[a-z0-9]{3,}", str(c.get("title", "")).lower())):
            hits.setdefault(tok, []).append(c.get("address"))
    multi = {t: addrs for t, addrs in hits.items() if len(addrs) >= 2}
    assert multi, "need ≥2 windows sharing a title token for the ambiguity test"
    return sorted(multi, key=lambda t: (-len(multi[t]), t))[0]


def test_no_misfocus(live_state):
    clients = json.loads(hyprctl("clients", "-j"))
    token = _ambiguous_title_token(clients)
    before = json.loads(hyprctl("activewindow", "-j")).get("address")
    r = handle_focus_window({"title": token})
    assert r.code == "error", f"expected error Result on ambiguous title, got {r!r}"
    assert "ambiguous" in r.detail, f"error should say ambiguous: {r.detail!r}"
    after = json.loads(hyprctl("activewindow", "-j")).get("address")
    assert after == before, f"focus moved on ambiguous title: {before} -> {after}"
