"""Gate: no player running → error `Result`, not a crash (pytest exits 0)."""
import asyncio

import pytest

from executor.music import BUS_PREFIX, handle_music

BOGUS = "org.mpris.MediaPlayer2.KyumaDoesNotExist"


def test_no_player_pinned():
    """Pinned-but-absent player → error Result for ops and status."""
    for op in ("toggle", "next", "status"):
        r = handle_music({"op": op, "player": BOGUS})
        assert r.code == "error", f"{op}: {r.detail!r}"


def _bus_player_names():
    async def main():
        from dbus_next.aio import MessageBus
        from dbus_next import BusType

        bus = MessageBus(bus_type=BusType.SESSION)
        await bus.connect()
        try:
            daemon = bus.get_proxy_object(
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                await bus.introspect("org.freedesktop.DBus", "/org/freedesktop/DBus"),
            )
            return await daemon.get_interface("org.freedesktop.DBus").call_list_names()
        finally:
            bus.disconnect()

    return asyncio.run(asyncio.wait_for(main(), 10))


def test_no_player_autodetect():
    """Literal doc case: with no player on the bus, auto-detect errors."""
    try:
        names = _bus_player_names()
    except Exception as e:  # noqa: BLE001 — no bus means nothing to detect
        pytest.skip(f"session bus required: {e}")
    present = sorted(n for n in names if n.startswith(BUS_PREFIX))
    if present:
        pytest.skip(f"real player(s) on bus, cannot stage absence: {present}")
    r = handle_music({"op": "toggle"})
    assert r.code == "error", r.detail
