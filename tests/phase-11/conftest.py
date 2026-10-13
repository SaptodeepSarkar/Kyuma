"""Phase 11 shared fixture: require audio stack, snapshot + restore mixer state."""
import subprocess

import pytest


def wpctl(*args):
    proc = subprocess.run(["wpctl", *args], capture_output=True, text=True, timeout=10)
    if proc.returncode != 0:
        raise RuntimeError(f"wpctl {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def parse_volume(out):
    """Parse `wpctl get-volume` output -> (percent int, muted bool)."""
    level = round(float(out.split("Volume:")[1].split()[0]) * 100)
    return level, "[MUTED]" in out


@pytest.fixture
def audio_state():
    """Skip when no audio stack; else snapshot volume/mute, restore after."""
    try:
        saved = parse_volume(wpctl("get-volume", "@DEFAULT_AUDIO_SINK@"))
    except (RuntimeError, OSError, ValueError, IndexError) as e:
        pytest.skip(f"audio stack required: {e}")
    yield {"level": saved[0], "muted": saved[1]}
    # Restore saved level + mute flag. Best-effort, never fails the gate.
    try:
        wpctl("set-volume", "@DEFAULT_AUDIO_SINK@", f"{saved[0] / 100:.4f}")
        wpctl("set-mute", "@DEFAULT_AUDIO_SINK@", "1" if saved[1] else "0")
    except Exception as e:  # noqa: BLE001 — restore must not fail the gate
        print(f"\nWARNING: audio restore failed: {e}")
