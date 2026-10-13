"""Phase 02 — VAD gate: mic/file → speech chunks; silence emits nothing.

Live-mic backend is ``pw-record`` (PipeWire). File input is stdlib ``wave``
(16-bit PCM; multi-channel is averaged to mono). No third-party deps.

Contract note: Phase 01 has not landed yet, so there is no contracts module
to import. ``SpeechChunk`` carries ``(start, end)`` seconds, the same shape
the future ``Word{w:text, t:float}`` stream builds on — re-export or adapt
this type when ``Phase 01`` freezes schemas.
"""
from __future__ import annotations

import shutil
import signal
import struct
import subprocess
import tempfile
import wave
from dataclasses import dataclass, field


@dataclass
class VadConfig:
    frame_ms: int = 30        # scoring frame length
    threshold_rms: float = 500.0  # frames at/above this RMS count as speech
    min_speech_ms: int = 90   # consecutive speech frames needed to open a chunk
    min_silence_ms: int = 300  # consecutive silence frames needed to close a chunk


@dataclass
class SpeechChunk:
    start: float       # seconds, inclusive
    end: float         # seconds, exclusive
    pcm: bytes         # mono s16le bytes for [start, end)
    sample_rate: int


def _frame_rms(frame: bytes) -> float:
    n = len(frame) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack("<%dh" % n, frame)
    return (sum(s * s for s in samples) / n) ** 0.5


def process_pcm(pcm: bytes, sample_rate: int,
                config: VadConfig = VadConfig()) -> list[SpeechChunk]:
    """Split mono s16le PCM into speech chunks. Pure silence → []."""
    frame_len = max(1, int(sample_rate * config.frame_ms / 1000))
    frame_bytes = frame_len * 2
    need_speech = max(1, (config.min_speech_ms + config.frame_ms - 1) // config.frame_ms)
    need_silence = max(1, (config.min_silence_ms + config.frame_ms - 1) // config.frame_ms)

    chunks: list[SpeechChunk] = []
    in_chunk = False
    run_speech = 0      # consecutive speech frames (pre-chunk: opening run)
    run_silence = 0     # consecutive silence frames while in chunk
    chunk_start_frame = 0
    last_speech_frame = 0

    n_frames = len(pcm) // frame_bytes
    for i in range(n_frames):
        frame = pcm[i * frame_bytes:(i + 1) * frame_bytes]
        speech = _frame_rms(frame) >= config.threshold_rms
        if not in_chunk:
            run_speech = run_speech + 1 if speech else 0
            if run_speech >= need_speech:
                in_chunk = True
                chunk_start_frame = i - need_speech + 1
                last_speech_frame = i
                run_silence = 0
        else:
            if speech:
                last_speech_frame = i
                run_silence = 0
            else:
                run_silence += 1
                if run_silence >= need_silence:
                    start = chunk_start_frame * frame_len / sample_rate
                    end = (last_speech_frame + 1) * frame_len / sample_rate
                    chunks.append(SpeechChunk(
                        start=start, end=end,
                        pcm=pcm[chunk_start_frame * frame_bytes:
                                (last_speech_frame + 1) * frame_bytes],
                        sample_rate=sample_rate))
                    in_chunk = False
                    run_speech = 0
                    run_silence = 0
    if in_chunk:  # file/stream ended mid-utterance: flush, don't drop
        start = chunk_start_frame * frame_len / sample_rate
        end = (last_speech_frame + 1) * frame_len / sample_rate
        chunks.append(SpeechChunk(
            start=start, end=end,
            pcm=pcm[chunk_start_frame * frame_bytes:
                    (last_speech_frame + 1) * frame_bytes],
            sample_rate=sample_rate))
    return chunks


def process_wav(path: str, on_chunk=None,
                config: VadConfig = VadConfig()) -> list[SpeechChunk]:
    """VAD over a wav file. ``on_chunk`` (the STT stub hook) is called once
    per speech chunk — and never for silence, so silence costs zero STT calls."""
    with wave.open(path, "rb") as w:
        nch, sw, rate, nframes = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(nframes)
    if sw != 2:
        raise ValueError(f"only 16-bit PCM supported, got {sw * 8}-bit: {path}")
    if nch > 1:  # average channels to mono
        samples = struct.unpack("<%dh" % (len(raw) // 2), raw)
        mono = [sum(samples[i * nch:(i + 1) * nch]) // nch
                for i in range(len(samples) // nch)]
        raw = struct.pack("<%dh" % len(mono), *mono)
    chunks = process_pcm(raw, rate, config)
    if on_chunk is not None:
        for c in chunks:
            on_chunk(c)
    return chunks


def capture_live(duration_s: float = 5.0, target: str | None = None,
                 config: VadConfig = VadConfig(),
                 on_chunk=None) -> list[SpeechChunk]:
    """Record the mic via ``pw-record`` for ``duration_s`` and VAD the result."""
    exe = shutil.which("pw-record")
    if exe is None:
        raise RuntimeError("pw-record not found: no mic backend on this host")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    cmd = [exe, "--rate", "16000", "--channels", "1", "--format", "s16", tmp]
    if target:
        cmd += ["--target", target]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        proc.wait(timeout=duration_s)
    except subprocess.TimeoutExpired:
        proc.send_signal(signal.SIGINT)  # SIGINT finalizes the wav header
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    return process_wav(tmp, on_chunk=on_chunk, config=config)
