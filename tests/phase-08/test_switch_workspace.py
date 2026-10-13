"""Gate: switch away and back → active workspace matches (session restored)."""
import json

from conftest import hyprctl

from executor.hyprland import handle_switch_workspace


def test_switch_workspace(live_state):
    orig = live_state["workspace_id"]
    workspaces = json.loads(hyprctl("workspaces", "-j"))
    others = [w["id"] for w in workspaces if w["id"] != orig]
    assert others, "need ≥2 workspaces for the switch test"
    away = others[0]

    r = handle_switch_workspace({"n": away})
    assert r.code == 200, r.detail
    assert json.loads(hyprctl("activeworkspace", "-j"))["id"] == away

    r = handle_switch_workspace({"n": orig})
    assert r.code == 200, r.detail
    assert json.loads(hyprctl("activeworkspace", "-j"))["id"] == orig
