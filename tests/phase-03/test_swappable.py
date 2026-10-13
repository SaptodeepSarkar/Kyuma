"""Gate: model path is config-driven — a second model dir loads and decodes."""

import os

import pytest

from stt.loader import load_model, resolve_model_path

from conftest import SAMPLE_WAV, SECOND_MODEL


def test_second_model_transcribes():
    if not os.path.isdir(SECOND_MODEL):
        pytest.skip("second model not downloaded; config path still honored below")
    from stt.stream import StreamingRecognizer
    import wave

    rec = StreamingRecognizer(load_model(SECOND_MODEL))
    with wave.open(SAMPLE_WAV, "rb") as wf:
        data = wf.readframes(wf.getnframes())
    partial, final = rec.push(data)
    tail = rec.finalize()
    assert isinstance(partial, list) and isinstance(final, list)
    assert final or tail, "second model produced no words on speech audio"


def test_config_path_honored_not_default():
    assert resolve_model_path(SECOND_MODEL) == SECOND_MODEL
    assert resolve_model_path(SECOND_MODEL) != resolve_model_path()
    os.environ["KYUMA_STT_MODEL"] = SECOND_MODEL
    try:
        assert resolve_model_path() == SECOND_MODEL
    finally:
        del os.environ["KYUMA_STT_MODEL"]
