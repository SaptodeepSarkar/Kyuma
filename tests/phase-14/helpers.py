"""Shared helpers for phase-14 gates (plain module, imported by test files)."""
from __future__ import annotations

import subprocess


def wpctl(*args: str) -> str:
    proc = subprocess.run(["wpctl", *args], capture_output=True, text=True, timeout=10)
    if proc.returncode != 0:
        raise RuntimeError(f"wpctl {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def parse_volume(out: str) -> tuple[int, bool]:
    return round(float(out.split("Volume:")[1].split()[0]) * 100), "[MUTED]" in out


def make_words(*texts: str, step: float = 0.2) -> list:
    """Scripted STT Words (no live mic)."""
    from harness.contracts import Word

    return [Word(w=t, t=round(i * step, 3)) for i, t in enumerate(texts)]
