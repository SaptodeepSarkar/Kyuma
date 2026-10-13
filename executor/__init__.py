"""Phase 14 — central handler registration.

Handler modules self-register only on import (``apps``, ``browser``);
``volume``, ``brightness`` and ``hyprland`` expose plain handler functions.
Importing THIS package stays side-effect free on purpose: gate 07 asserts
dispatch routes every action to its stub, and ``import executor.dispatch``
runs this file first — eager registration here would replace those stubs
and turn gate 07 red. Registration happens only via ``register_all()``,
called explicitly by ``harness.loop`` (the only production consumer).
"""

from __future__ import annotations

_REGISTERED = False


def register_all() -> None:
    """Import every handler module, bind real handlers over dispatch stubs.

    Idempotent — safe to call from ``harness.loop`` import time and from
    every phase-14 test process. ``music`` is registered only if the Phase 13
    module exists and exposes ``handle_music``; otherwise its stub stays.
    """
    global _REGISTERED
    if _REGISTERED:
        return
    from executor import brightness, hyprland, volume
    from executor.dispatch import register_handler

    import executor.apps  # noqa: F401 -- side effect: registers open_app/focus_app
    import executor.browser  # noqa: F401 -- side effect: registers open_website/focus_website/web_search

    register_handler("volume", volume.handle_volume)
    register_handler("brightness", brightness.handle_brightness)
    register_handler("switch_workspace", hyprland.handle_switch_workspace)
    register_handler("focus_window", hyprland.handle_focus_window)
    try:
        import executor.music as music
    except ImportError:
        pass  # Phase 13 not built: music stub stays, dispatch still answers
    else:
        handler = getattr(music, "handle_music", None)
        if callable(handler):
            register_handler("music", handler)
    _REGISTERED = True
