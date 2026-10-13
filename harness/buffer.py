"""Phase 04 — harness word buffer (append-only).

Rules (chosen, dumb and explicit):
  COMPLETENESS: a batch is complete when its joined text ends with terminal
    punctuation (. ! ?) OR it holds >= MIN_WORDS words (default 3).
    Complete -> emit ONE sentence (words joined with single spaces, trailing
    punctuation stripped), clear the batch, stop appending to it.
    Incomplete -> return None, keep waiting (silence downstream).
  TIMEOUT: DISCARD. If no new word arrives within TIMEOUT_S (default 2.0s)
    of the last buffered word, the stalled fragment is discarded — nothing
    is emitted. Rationale: a stale fragment is likely abandoned speech;
    emitting it would dispatch a partial/wrong command, violating the
    flows.md rule "no partial dispatch". Fresh words after a stall start
    a new batch; staleness is judged on Word.t (STT timestamps), so this
    module needs no clock/hardware.

Word schema is the Phase-01 canonical ``harness.contracts.Word`` {w, t}.
"""

from __future__ import annotations

from dataclasses import dataclass, field

try:  # Phase-01 canonical contracts.
    from harness.contracts import Word
except ImportError:
    try:
        from contracts import Word  # type: ignore
    except ImportError:

        @dataclass(frozen=True)
        class Word:  # type: ignore[no-redef]
            """Fallback mirror of the Phase-01 Word schema {w, t}."""

            w: str
            t: float = 0.0


@dataclass
class Buffer:
    """Append-only word batcher; emits at most one sentence per batch."""

    min_words: int = 3
    timeout_s: float = 2.0
    pause_s: float = 0.8  # inter-word gap that ends a command (VAD-silence echo)
    _words: list = field(default_factory=list)

    @property
    def pending(self) -> list:
        return list(self._words)

    def _last_t(self) -> float | None:
        return self._words[-1].t if self._words else None

    def _stale(self, now: float) -> bool:
        last = self._last_t()
        return last is not None and (now - last) > self.timeout_s

    def check_timeout(self, now: float) -> None:
        """Discard stalled fragment; emit nothing."""
        if self._stale(now):
            self._words.clear()

    def _complete(self) -> bool:
        if not self._words:
            return False
        text = " ".join(w.w for w in self._words).strip()
        return text.endswith((".", "!", "?")) or len(self._words) >= 8

    def _snapshot(self) -> str:
        sentence = " ".join(w.w for w in self._words).strip().rstrip(".!?").strip()
        self._words.clear()
        return sentence

    def feed(self, word: Word) -> str | None:
        """Append one Word; return the sentence iff the batch just completed.

        Pause rule: a word arriving > pause_s after the previous one ends the
        prior command — emit the buffered batch first (if >= min_words),
        then start a fresh batch with the new word. Short fragments (<
        min_words) merge across pauses (slow speaker, same command); they
        act via utterance-end force-emit, never via timeout (which discards).
        """
        if self._stale(word.t):
            self._words.clear()  # stale fragment discarded, new batch starts
        elif (
            self._words
            and len(self._words) >= self.min_words
            and (word.t - self._words[-1].t) > self.pause_s
        ):
            sentence = self._snapshot()
            self._words.append(word)
            return sentence or None
        self._words.append(word)
        if not self._complete():
            return None
        return self._snapshot() or None
