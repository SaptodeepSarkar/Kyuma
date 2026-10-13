"""Shared fixtures for Phase 03 gates: repo import path + cached default model."""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SAMPLE_WAV = os.path.join(ROOT, "tests", "phase-03", "sample.wav")
SECOND_MODEL = os.path.join(ROOT, "models", "vosk-model-small-en-us-0.15")


@pytest.fixture(scope="session")
def model():
    from stt.loader import load_model

    return load_model()
