"""Frozen message schemas — Phase 01 contract. Import path: ``harness.contracts``.

Word: one STT token {w: text, t: seconds}. Exec: one decision {action, args}
where action is in ACTIONS (closed list from docs/components/implementation-harness.md).
Result: executor reply {code: 200 | "error", detail: str}.
All three are JSON-serializable (asdict -> json.dumps) for the HTTP/JSON IPC.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

# Closed action list; extended in phase 08 with switch_workspace/focus_window
# (full workspace + window control on Hyprland).
ACTIONS = (
    "open_app",
    "open_website",
    "focus_website",
    "focus_app",
    "web_search",
    "volume",
    "brightness",
    "music",
    "switch_workspace",
    "focus_window",
)


@dataclass(frozen=True)
class Word:
    w: str  # token text, non-empty
    t: float  # timestamp in seconds, >= 0

    def __post_init__(self) -> None:
        if not isinstance(self.w, str) or not self.w:
            raise ValueError(f"Word.w must be a non-empty str, got {self.w!r}")
        if isinstance(self.t, bool) or not isinstance(self.t, (int, float)) or self.t < 0:
            raise ValueError(f"Word.t must be a number >= 0, got {self.t!r}")
        object.__setattr__(self, "t", float(self.t))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Word":
        if not isinstance(d, dict):
            raise TypeError(f"Word must decode from a dict, got {type(d).__name__}")
        try:
            return cls(w=d["w"], t=d["t"])
        except KeyError as e:
            raise ValueError(f"Word missing field: {e}") from e


@dataclass(frozen=True)
class Exec:
    action: str  # one of ACTIONS
    args: dict[str, Any]  # per-action parameters

    def __post_init__(self) -> None:
        if self.action not in ACTIONS:
            raise ValueError(f"Exec.action must be one of {ACTIONS}, got {self.action!r}")
        if not isinstance(self.args, dict):
            raise TypeError(f"Exec.args must be a dict, got {type(self.args).__name__}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Exec":
        if not isinstance(d, dict):
            raise TypeError(f"Exec must decode from a dict, got {type(d).__name__}")
        try:
            return cls(action=d["action"], args=d["args"])
        except KeyError as e:
            raise ValueError(f"Exec missing field: {e}") from e


@dataclass(frozen=True)
class Result:
    code: Any  # 200 (int) on success, "error" (str) on failure
    detail: str

    def __post_init__(self) -> None:
        if self.code != 200 and self.code != "error":
            raise ValueError(f'Result.code must be 200 or "error", got {self.code!r}')
        if not isinstance(self.detail, str):
            raise TypeError(f"Result.detail must be a str, got {type(self.detail).__name__}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Result":
        if not isinstance(d, dict):
            raise TypeError(f"Result must decode from a dict, got {type(d).__name__}")
        try:
            return cls(code=d["code"], detail=d["detail"])
        except KeyError as e:
            raise ValueError(f"Result missing field: {e}") from e
