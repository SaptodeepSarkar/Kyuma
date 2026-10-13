"""Phase 01 gate: repo skeleton exists."""
import os

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")

EXPECTED_DIRS = ["stt", "harness", "executor", "model-server", "ui", "tests/phase-01", "models"]
EXPECTED_FILES = ["docs/PHASES/phase-01-scaffold-contracts.md"]


def test_layout_dirs_exist():
    for d in EXPECTED_DIRS:
        assert os.path.isdir(os.path.join(ROOT, d)), f"missing dir: {d}"


def test_phase_doc_exists():
    for f in EXPECTED_FILES:
        assert os.path.isfile(os.path.join(ROOT, f)), f"missing file: {f}"
