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
    threshold_rms: float = 500.0  # floor when adaptive is off (see below)
    min_speech_ms: int = 90   # consecutive speech frames needed to open a chunk
    min_silence_ms: int = 300  # consecutive silence frames needed to close a chunk
    adaptive: bool = False    # live capture turns this on; file fixtures keep
                              # the fixed threshold (a constant tone has no floor)
    margin_db: float = 9.0    # speech must beat the floor by this much
    floor_alpha: float = 0.05  # noise-floor tracker speed (per frame)


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
    # Adaptive gate: a constant loud hash (~20k RMS on this laptop's builtin
    # mic) sits far above any fixed 500-RMS threshold, so the gate stayed open
    # every window and Vosk was fed noise (phantom words). Track the floor and
    # require speech to beat it by margin_db.
    floor = None
    margin = 10 ** (config.margin_db / 20)
    for i in range(n_frames):
        frame = pcm[i * frame_bytes:(i + 1) * frame_bytes]
        rms = _frame_rms(frame)
        if config.adaptive:
            if floor is None:
                floor = rms
            elif rms < floor:
                floor = rms                      # fast down: nice quiet is real
            else:
                floor += config.floor_alpha * (rms - floor)
            gate = max(floor * margin, config.threshold_rms)
            speech = rms >= gate
        else:
            speech = rms >= config.threshold_rms
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


def _resample_mono(pcm: bytes, src_rate: int, dst_rate: int = 16000) -> bytes:
    """Mono s16le -> dst_rate. Integer-ratio block average (crude lowpass,
    no alias garbage); linear interp otherwise. STT-grade, not hi-fi."""
    if src_rate == dst_rate:
        return pcm
    n = len(pcm) // 2
    samples = struct.unpack("<%dh" % n, pcm)
    if src_rate % dst_rate == 0:
        step = src_rate // dst_rate
        out = [sum(samples[i * step:(i + 1) * step]) // step
               for i in range(n // step)]
    else:
        m = int(n * dst_rate / src_rate)
        out = [int(samples[int(i * n / m)] +
                   (samples[min(n - 1, int(i * n / m) + 1)] -
                    samples[int(i * n / m)]) * ((i * n / m) % 1))
               for i in range(m)]
    return struct.pack("<%dh" % len(out), *[max(-32768, min(32767, v)) for v in out])


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
    if rate != 16000:  # STT models are 16k-only; convert file input
        raw = _resample_mono(raw, rate, 16000)
        rate = 16000
    chunks = process_pcm(raw, rate, config)
    if on_chunk is not None:
        for c in chunks:
            on_chunk(c)
    return chunks


def capture_live(duration_s: float = 5.0, target: str | None = None,
                 config: VadConfig = VadConfig(),
                 on_chunk=None, skip_ms: int = 250) -> list[SpeechChunk]:
    """Record the mic via ``pw-record`` for ``duration_s`` and VAD the result.

    Drops the first ``skip_ms`` (device settle transient: often full-scale
    flatline that would fake a speech chunk and poison noise profiles).
    Enables the adaptive noise-floor gate: this laptop's builtin mic has a
    constant hash far above any fixed threshold, which held the gate open."""
    from dataclasses import replace
    config = replace(config, adaptive=True) if not config.adaptive else config
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
    if skip_ms > 0:
        with wave.open(tmp, "rb") as w:
            params = w.getparams()
            rate = w.getframerate()
            raw = w.readframes(w.getnframes())
        cut = min(len(raw), int(rate * skip_ms / 1000) * params.sampwidth * params.nchannels)
        with wave.open(tmp, "wb") as w:
            w.setparams(params)
            w.writeframes(raw[cut:])
    return process_wav(tmp, on_chunk=on_chunk, config=config)
