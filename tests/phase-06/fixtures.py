"""Phase 06 fixture: >=5 phrasings x 8 intents (40+ sentences) + gibberish set."""
from __future__ import annotations

# sentence -> expected action. 6 phrasings per intent = 60 sentences.
CASES: list[tuple[str, str]] = [
    # open_app
    ("open firefox", "open_app"),
    ("launch the terminal", "open_app"),
    ("start obs studio", "open_app"),
    ("open the file manager", "open_app"),
    ("launch discord", "open_app"),
    ("start up vlc", "open_app"),
    # open_website
    ("open youtube", "open_website"),
    ("go to github dot com", "open_website"),
    ("open stack overflow in the browser", "open_website"),
    ("launch reddit", "open_website"),
    ("open google maps", "open_website"),
    ("take me to wikipedia", "open_website"),
    # focus_website
    ("focus the youtube tab", "focus_website"),
    ("switch to the gmail tab", "focus_website"),
    ("go to the github tab", "focus_website"),
    ("bring up the docs tab", "focus_website"),
    ("show me the calendar tab", "focus_website"),
    ("switch back to the youtube tab", "focus_website"),
    # focus_app
    ("focus the terminal", "focus_app"),
    ("switch to discord", "focus_app"),
    ("bring up firefox", "focus_app"),
    ("go to vscode", "focus_app"),
    ("show me obs", "focus_app"),
    ("switch back to vlc", "focus_app"),
    # web_search
    ("search for the weather today", "web_search"),
    ("google who won the match yesterday", "web_search"),
    ("look up the capital of norway", "web_search"),
    ("what is the time in tokyo", "web_search"),
    ("search how to tie a tie", "web_search"),
    ("who is the president of france", "web_search"),
    # volume
    ("turn the volume up", "volume"),
    ("lower the volume", "volume"),
    ("mute the sound", "volume"),
    ("unmute the audio", "volume"),
    ("set volume to fifty percent", "volume"),
    ("volume down a bit", "volume"),
    # brightness
    ("turn the brightness up", "brightness"),
    ("dim the screen", "brightness"),
    ("set brightness to seventy", "brightness"),
    ("increase screen brightness", "brightness"),
    ("lower the display brightness", "brightness"),
    ("brightness to max", "brightness"),
    # music
    ("play the music", "music"),
    ("pause the song", "music"),
    ("next song", "music"),
    ("skip this track", "music"),
    ("go back to the previous song", "music"),
    ("stop the music", "music"),
    # switch_workspace
    ("switch to workspace three", "switch_workspace"),
    ("go to workspace 2", "switch_workspace"),
    ("move to the coding workspace", "switch_workspace"),
    ("switch to workspace five", "switch_workspace"),
    ("change to workspace one", "switch_workspace"),
    ("go to the second workspace", "switch_workspace"),
    # focus_window
    ("focus the downloads window", "focus_window"),
    ("switch to the settings window", "focus_window"),
    ("bring up the properties window", "focus_window"),
    ("focus the window titled inbox", "focus_window"),
    ("go to the preferences window", "focus_window"),
    ("show me the terminal window", "focus_window"),
]

# Non-command speech: greetings, questions, dictation, fragments, ASR garbage.
# Expected behavior: safe noop (validate_exec raises) — never a real action.
GIBBERISH: list[str] = [
    "hello there",
    "good morning",
    "thanks a lot",
    "hmm let me think about that report",
    "the quarterly results were actually pretty good",
    "so I told him we should meet on tuesday",
    "uh yeah maybe sort of",
    "banana pancake elephant",
    "asdf qwer zxcv",
    "blah blah blah",
    "can you hear me",
    "what time is it oh never mind",
    "I wonder what's for lunch today",
    "this meeting could have been an email",
    "the cat sat on the mat",
]


def decide_on(server: str, sentence: str) -> dict:
    """decide() with per-model /no_think control (DECIDE_NO_THINK=1 for Qwen3).

    Default off: the bake-off winner (Qwen2.5-1.5B, non-thinking) serves :8081.
    Qwen3 legs were run with DECIDE_NO_THINK=1 (its thinking ignores the
    `enable_thinking` flag on some server builds; the suffix is template-native).
    """
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "model-server"))
    from decide_prompt import decide
    return decide(server, sentence, no_think=os.environ.get("DECIDE_NO_THINK", "0") == "1")
