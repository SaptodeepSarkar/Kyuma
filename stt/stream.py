"""Streaming partial+final ``Word`` emission over a Vosk recognizer.

Contract (Phase 01): ``Word{w:text, t:float}`` where ``t`` is seconds since
stream start. Speech chunks in (raw 16-bit PCM) → word stream out.
Silence in → nothing out (VAD-gating lives in ``stt/vad.py`` when Phase 02
lands; until then callers feed raw chunks straight here).
"""

import json

from harness.contracts import Word

SAMPLE_RATE = 16000


def _words(result, t):
    return [Word(w["word"], float(t)) for w in result.get("result", [])]


class StreamingRecognizer:
    """Wraps ``KaldiRecognizer``; ``push`` returns ``(partial, final)`` words."""

    def __init__(self, model, sample_rate=SAMPLE_RATE):
        from vosk import KaldiRecognizer

        self.rec = KaldiRecognizer(model, sample_rate)
        self.rec.SetWords(True)
        self.sample_rate = sample_rate
        self.consumed = 0  # PCM bytes fed so far

    def push(self, pcm: bytes):
        """Feed one chunk. Returns ``(partial_words, final_words)``."""
        t = self.consumed / (2 * self.sample_rate)
        self.consumed += len(pcm)
        if self.rec.AcceptWaveform(pcm):
            return [], _words(json.loads(self.rec.Result()), t)
        text = json.loads(self.rec.PartialResult()).get("partial", "").strip()
        partial = [Word(w, float(t)) for w in text.split()] if text else []
        return partial, []

    def finalize(self):
        """Flush remaining audio. Returns leftover final ``Word``s."""
        t = self.consumed / (2 * self.sample_rate)
        return _words(json.loads(self.rec.FinalResult()), t)


def transcribe_wav(path, model, chunk_frames=2000):
    """Yield ``("partial"|"final", [Word])`` events for a 16kHz mono wav."""
    import wave

    rec = StreamingRecognizer(model)
    with wave.open(path, "rb") as wf:
        if wf.getframerate() != rec.sample_rate or wf.getnchannels() != 1:
            raise ValueError(f"{path}: need 16kHz mono wav")
        while True:
            data = wf.readframes(chunk_frames)
            if not data:
                break
            partial, final = rec.push(data)
            if partial:
                yield "partial", partial
            if final:
                yield "final", final
    tail = rec.finalize()
    if tail:
        yield "final", tail
