"""Phase 06 — decision JSON: flat Exec schema, system prompt, validator, client.

Grammar is invisible to the model, so SYSTEM_PROMPT mirrors EXEC_SCHEMA exactly:
same action names, same arg keys. Served via llama.cpp with
``response_format: json_schema``, temp 0, ``enable_thinking=False`` (Qwen3 thinks
by default; think-tokens would blow the latency budget).

Grammar enum = 8 Exec actions + ``noop``. ``noop`` is NOT in
``harness.contracts.ACTIONS`` (frozen Phase 01 contract): ``validate_exec``
rejects it with ValueError and the harness treats that as do-nothing. This is
the gibberish guard — small models over-call when prompted hard, and a grammar
without a safe exit forces a wild action.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any

from harness.contracts import ACTIONS, Exec

# Closed action list, mirrored from harness.contracts (import, don't duplicate).
# Grammar-only safe exit for non-command speech; never a valid Exec.
NOOP = "noop"
GRAMMAR_ACTIONS = (*ACTIONS, NOOP)

# Flat schema: no conditionals / nested $refs (llama.cpp can't enforce them).
# args stays a free-form object in the grammar; per-action arg shapes live in
# the prompt text + the lenient second gate below.
EXEC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": list(GRAMMAR_ACTIONS)},
        "args": {"type": "object"},
    },
    "required": ["action", "args"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are Kyuma, a voice-command router. Output ONE JSON object only: {"action": ..., "args": {...}}.

Actions and their args (use exactly these keys):
- open_app: {"app": "<app name>"} — launch an app. e.g. "open firefox" -> {"action":"open_app","args":{"app":"firefox"}}
- open_website: {"site": "<site name or url>"} — open a new site. e.g. "open youtube" -> {"action":"open_website","args":{"site":"youtube"}}
- focus_website: {"site": "<tab title or site>"} — switch to an ALREADY OPEN browser tab. "focus", "switch to", "go to the tab" mean this, not open_website.
- focus_app: {"app": "<app name>"} — switch to an ALREADY OPEN app window. "focus", "switch to", "bring up" mean this, not open_app.
- web_search: {"query": "<search text>"} — search the web. "search", "google", "look up", "what is", "who is" mean this.
- volume: {"op": "up|down|mute|unmute|set", "level": <0-100, only for set>} — e.g. "mute" -> {"action":"volume","args":{"op":"mute"}}
- brightness: {"op": "up|down|set", "level": <0-100, only for set>} — e.g. "brightness to 70" -> {"action":"brightness","args":{"op":"set","level":70}}
- music: {"op": "play|pause|next|prev|stop"} — e.g. "next song" -> {"action":"music","args":{"op":"next"}}
- switch_workspace: {"workspace": "<number or name>"} — switch desktop workspace. e.g. "switch to workspace 3" -> {"action":"switch_workspace","args":{"workspace":"3"}}
- focus_window: {"window": "<window title>"} — focus a window by its title. "window" + a title means this, not focus_app. e.g. "focus the downloads window" -> {"action":"focus_window","args":{"window":"downloads"}}

Rules:
- open_app: "open"/"launch"/"start" + app name (firefox, terminal, discord, vlc, obs...). e.g. "start up vlc" -> {"action":"open_app","args":{"app":"vlc"}}
- open_website: "open"/"launch"/"go to"/"take me to" + site/service name, domain, or "dot com" (youtube, reddit, maps, wikipedia, github...). e.g. "launch reddit" -> {"action":"open_website","args":{"site":"reddit"}}; "take me to wikipedia" -> {"action":"open_website","args":{"site":"wikipedia"}}
  Named websites (youtube, reddit, google maps, wikipedia, github, stack overflow) are ALWAYS open_website, never apps — even with "open"/"launch". e.g. "go to github dot com" -> {"action":"open_website","args":{"site":"github"}}.
- focus_website: ONLY when the sentence contains the word "tab". e.g. "focus the youtube tab" -> {"action":"focus_website","args":{"site":"youtube"}}
- focus_app: switch/focus/bring/show + app name, with NO word "window"/"tab"/"workspace". e.g. "switch to discord" -> {"action":"focus_app","args":{"app":"discord"}}; "go to vscode" -> {"action":"focus_app","args":{"app":"vscode"}}
- focus_window: ONLY when the sentence contains the word "window". e.g. "focus the downloads window" -> {"action":"focus_window","args":{"window":"downloads"}}; "bring up the properties window" -> {"action":"focus_window","args":{"window":"properties"}}
- switch_workspace: ONLY when the sentence contains the word "workspace". "switch to discord" is focus_app, never switch_workspace. e.g. "go to workspace 2" -> {"action":"switch_workspace","args":{"workspace":"2"}}; "move to the coding workspace" -> {"action":"switch_workspace","args":{"workspace":"coding"}}
- web_search: ONLY for questions or explicit search verbs ("search", "google", "look up", "what is", "who is"). Plain statements, opinions, and chatter are NEVER web_search. e.g. "what is the time in tokyo" -> {"action":"web_search","args":{"query":"time in tokyo"}}; "the quarterly results were pretty good" -> noop; "I wonder what's for lunch" -> noop.
- "go to" disambiguation: "go to" + site/domain/dot-com = open_website; "go to" + app name = focus_app. "go to" NEVER means focus_website/focus_window unless the sentence contains "tab"/"window". e.g. "go to vscode" has no word "window" -> focus_app, never focus_window.
- music: play/pause/next/previous/skip/stop + song/music/track. e.g. "skip this track" -> {"action":"music","args":{"op":"next"}}
  "skip", "skip this", "next song", "next track" ALWAYS mean music-next, never noop.
- If the sentence is NOT a command (greeting, statement, opinion, dictation, gibberish, thinking aloud), output {"action":"noop","args":{}}. When unsure between a real action and noop, choose noop. Never guess a real action for non-commands.
- Output compact JSON on one line, no other text."""


def build_request(sentence: str, no_think: bool = True) -> dict[str, Any]:
    """llama.cpp /v1/chat/completions body: temp 0, thinking off, GBNF schema."""
    # The "/no_think" suffix is load-bearing for accuracy (bake-off 96.7%
    # was measured WITH it; dropping it flips edge cases like "skip this
    # track"). The model occasionally echoes it as an arg value, which
    # harness.loop.normalize strips. Qwen2.5 has no thinking mode anyway.
    user = sentence + " /no_think" if no_think else sentence
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": sentence},
        ],
        "temperature": 0.0,
        "enable_thinking": False,  # honored by newer servers; /no_think covers the rest
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "Exec", "strict": True, "schema": EXEC_SCHEMA},
        },
        "max_tokens": 128,
    }


def decide(server: str, sentence: str, timeout: float = 30.0, no_think: bool = True) -> dict[str, Any]:
    """POST one sentence to a llama-server chat endpoint; return parsed JSON obj."""
    body = json.dumps(build_request(sentence, no_think=no_think)).encode()
    req = urllib.request.Request(
        f"{server.rstrip('/')}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.load(resp)
    content = payload["choices"][0]["message"]["content"]
    return json.loads(content)


def validate_exec(obj: dict[str, Any]) -> Exec:
    """Second gate after GBNF: grammar guarantees shape, this guarantees sense.

    Raises ValueError on noop / bad action / bad args — caller treats as no-op.
    Hand-validated (no pydantic dep); args kept lenient so executor phases own
    per-action strictness. shortcut: per-action required-arg checks, when an
    executor phase needs them.
    """
    if not isinstance(obj, dict):
        raise ValueError(f"Exec must be an object, got {type(obj).__name__}")
    action = obj.get("action")
    if action == NOOP:
        raise ValueError("noop: not a command, do nothing")
    if action not in ACTIONS:
        raise ValueError(f"Exec.action must be one of {ACTIONS}, got {action!r}")
    args = obj.get("args")
    if not isinstance(args, dict):
        raise ValueError(f"Exec.args must be an object, got {args!r}")
    return Exec(action=action, args=args)
