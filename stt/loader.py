"""Config-driven STT model loader.

The model path is never hardcoded at call sites. Resolution order:
explicit argument > ``KYUMA_STT_MODEL`` env var > repo default
(``models/vosk-model-small-en-in-0.4``). Any Vosk model directory works.
"""

import os

DEFAULT_MODEL_DIR = "models/vosk-model-small-en-in-0.4"  # repo-relative default

ENV_VAR = "KYUMA_STT_MODEL"


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_model_path(model_path=None):
    """Return the model directory to load, honoring arg > env > default."""
    if model_path:
        return model_path
    env = os.environ.get(ENV_VAR)
    if env:
        return env
    return os.path.join(_repo_root(), DEFAULT_MODEL_DIR)


def load_model(model_path=None):
    """Load and return a Vosk ``Model`` from the resolved config path."""
    from vosk import Model

    path = resolve_model_path(model_path)
    if not os.path.isdir(path):
        raise FileNotFoundError(f"STT model dir not found: {path}")
    return Model(path)
