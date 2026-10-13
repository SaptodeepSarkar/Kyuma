"""Phase 12 shared fixture: require backlight device, snapshot + restore brightness."""
import pytest

from executor.brightness import handle_brightness_get, handle_brightness_set
from executor.dispatch import register_handler
from executor.brightness import handle_brightness


@pytest.fixture
def backlight():
    """Skip when no backlight device; else snapshot %, restore after (best-effort)."""
    register_handler("brightness", handle_brightness)
    r = handle_brightness_get({})
    if r.code != 200:
        pytest.skip(f"backlight device required: {r.detail}")
    try:
        saved = int(r.detail.split()[1].rstrip("%"))
    except (IndexError, ValueError):
        pytest.skip(f"unparseable brightness detail: {r.detail!r}")
    yield saved
    # Restore snapshot. Best-effort, never fails the gate.
    try:
        if saved <= 0:
            handle_brightness_set({"value": saved, "force": True})
        else:
            handle_brightness_set({"value": saved})
    except Exception as e:  # noqa: BLE001 — restore must not fail the gate
        print(f"\nWARNING: brightness restore failed: {e}")
