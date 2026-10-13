"""Phase 13 — music control via MPRIS on the session bus.

Backend choice: pure-Python MPRIS over D-Bus via ``dbus-next`` (installed
into the shared ``.venv``) — no ``playerctl`` binary exists on this box, and
sudo is not assumed, so a subprocess backend is out. ``dbus-next`` was picked
over ``jeepney`` because exporting the fake test player (``ServiceInterface``)
is one class, while jeepney would need a hand-rolled message loop.

Ops (``handle_music({"op": ...})`` → ``Result``):
play | pause | toggle | next | prev | status (default). Every success reports
``"<PlaybackStatus> — <title>"``. Optional ``{"player": <bus name>}`` pins a
player (gate tests pin the fake); otherwise the first
``org.mpris.MediaPlayer2.*`` name wins. No player (or an unknown pinned name)
→ error ``Result``, never a raise. Importing this module registers the
``music`` handler (the dispatch router is untouched).
"""
from __future__ import annotations

import asyncio
from typing import Any

from harness.contracts import Result

from executor.dispatch import register_handler

try:
    from dbus_next import BusType, Variant
    from dbus_next.aio import MessageBus
except ImportError as e:  # handler degrades to an error Result (see below)
    _IMPORT_ERROR: Exception | None = e
    BusType = Variant = MessageBus = None  # type: ignore[assignment]
else:
    _IMPORT_ERROR = None

BUS_PREFIX = "org.mpris.MediaPlayer2."
OBJ_PATH = "/org/mpris/MediaPlayer2"
PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
PROPS_IFACE = "org.freedesktop.DBus.Properties"

_METHODS = {
    "play": "call_play",
    "pause": "call_pause",
    "toggle": "call_play_pause",
    "next": "call_next",
    "prev": "call_previous",
}


class _NoPlayer(RuntimeError):
    """Raised when no MPRIS player answers; mapped to an error Result."""


def _title_of(meta: Any) -> str:
    """Best-effort track label from an MPRIS Metadata dict."""
    try:
        title = meta.get("xesam:title")
        title = title.value if isinstance(title, Variant) else title
        if title:
            return str(title)
        trackid = meta.get("mpris:trackid")
        trackid = trackid.value if isinstance(trackid, Variant) else trackid
        if trackid:
            return str(trackid).rstrip("/").rsplit("/", 1)[-1]
    except Exception:  # noqa: BLE001 — label is best-effort only
        pass
    return "?"


async def _operate(op: str, player: str | None) -> str:
    """One D-Bus session: resolve player, run op, return ``"STATUS — title"``."""
    bus = MessageBus(bus_type=BusType.SESSION)
    await bus.connect()
    try:
        name = player
        if name is None:
            daemon = bus.get_proxy_object(
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                await bus.introspect("org.freedesktop.DBus", "/org/freedesktop/DBus"),
            )
            names = sorted(await daemon.get_interface("org.freedesktop.DBus").call_list_names())
            names = [n for n in names if n.startswith(BUS_PREFIX)]
            if not names:
                raise _NoPlayer("no MPRIS player on the session bus")
            name = names[0]
        obj = bus.get_proxy_object(name, OBJ_PATH, await bus.introspect(name, OBJ_PATH))
        if op != "status":
            await getattr(obj.get_interface(PLAYER_IFACE), _METHODS[op])()
        props = obj.get_interface(PROPS_IFACE)
        status = (await props.call_get(PLAYER_IFACE, "PlaybackStatus")).value
        try:
            meta = (await props.call_get(PLAYER_IFACE, "Metadata")).value
        except Exception:  # noqa: BLE001 — some players omit Metadata
            meta = {}
        return f"{status} — {_title_of(meta)}"
    finally:
        bus.disconnect()


def handle_music(args: dict[str, Any]) -> Result:
    """Music ops. ``args``: {"op": play|pause|toggle|next|prev|status, "player": bus name}."""
    if _IMPORT_ERROR is not None:
        return Result(code="error", detail=f"dbus-next required: {_IMPORT_ERROR}")
    if not isinstance(args, dict):
        return Result(code="error", detail="args must be a dict")
    op = args.get("op", "status")
    if op not in _METHODS and op != "status":
        return Result(code="error", detail=f"unknown music op: {op!r} (play|pause|toggle|next|prev|status)")
    player = args.get("player")
    if player is not None and (not isinstance(player, str) or not player.startswith(BUS_PREFIX)):
        return Result(code="error", detail=f"unknown player: {player!r}")

    async def runner() -> str:
        return await asyncio.wait_for(_operate(op, player), 10)

    try:
        return Result(code=200, detail=asyncio.run(runner()))
    except _NoPlayer as e:
        return Result(code="error", detail=str(e))
    except Exception as e:  # noqa: BLE001 — handler never raises (dispatch contract)
        return Result(code="error", detail=f"music {op} failed: {e}")


register_handler("music", handle_music)
