"""Phase 13 shared fixture: fake MPRIS player on the session bus.

The fake is an in-process ``dbus-next`` service
(``org.mpris.MediaPlayer2.KyumaTest``) with a 3-track playlist. Tests drive it
through the real ``handle_music`` D-Bus client path while reading ground truth
straight off the fake object — no real player needed. Skips with a reason when
the session bus is unreachable.
"""
import asyncio
import threading

import pytest

try:
    from dbus_next import BusType, Variant
    from dbus_next.aio import MessageBus
    from dbus_next.constants import RequestNameReply
    from dbus_next.service import ServiceInterface, dbus_property, method, PropertyAccess
except ImportError as e:
    _IMPORT_ERROR: Exception | None = e
else:
    _IMPORT_ERROR = None

from executor.dispatch import register_handler
from executor.music import handle_music

register_handler("music", handle_music)

BUS_NAME = "org.mpris.MediaPlayer2.KyumaTest"
OBJ_PATH = "/org/mpris/MediaPlayer2"
PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
TRACKS = ["track-a", "track-b", "track-c"]


if _IMPORT_ERROR is None:

    class _FakePlayerIface(ServiceInterface):
        def __init__(self) -> None:
            super().__init__(PLAYER_IFACE)
            self.status = "Paused"
            self.index = 0

        @dbus_property(access=PropertyAccess.READ)
        def PlaybackStatus(self) -> "s":
            return self.status

        @dbus_property(access=PropertyAccess.READ)
        def Metadata(self) -> "a{sv}":
            return {
                "mpris:trackid": Variant("o", f"/org/mpris/KyumaTest/Track/{self.index}"),
                "xesam:title": Variant("s", TRACKS[self.index]),
            }

        @method()
        def Play(self) -> None:
            self.status = "Playing"

        @method()
        def Pause(self) -> None:
            self.status = "Paused"

        @method()
        def PlayPause(self) -> None:
            self.status = "Paused" if self.status == "Playing" else "Playing"

        @method()
        def Next(self) -> None:
            self.index = (self.index + 1) % len(TRACKS)

        @method()
        def Previous(self) -> None:
            self.index = (self.index - 1) % len(TRACKS)

    class FakePlayer:
        """Live fake player; truth via attributes, control via D-Bus."""

        def __init__(self) -> None:
            self.iface = _FakePlayerIface()
            self._stop = threading.Event()
            self._ready = threading.Event()
            self._err: list[Exception] = []
            self._thread = threading.Thread(target=self._serve, daemon=True)

        @property
        def status(self) -> str:
            return self.iface.status

        @property
        def track(self) -> str:
            return TRACKS[self.iface.index]

        def reset(self, status: str = "Paused", index: int = 0) -> None:
            self.iface.status = status
            self.iface.index = index

        def _serve(self) -> None:
            async def main() -> None:
                bus = MessageBus(bus_type=BusType.SESSION)
                await bus.connect()
                try:
                    bus.export(OBJ_PATH, self.iface)
                    reply = await bus.request_name(BUS_NAME)
                    if reply != RequestNameReply.PRIMARY_OWNER:
                        raise RuntimeError(f"could not own {BUS_NAME}: {reply}")
                    self._ready.set()
                    while not self._stop.is_set():
                        await asyncio.sleep(0.05)
                finally:
                    bus.disconnect()

            try:
                asyncio.run(main())
            except Exception as e:  # noqa: BLE001 — surfaced as a skip reason
                self._err.append(e)
                self._ready.set()


@pytest.fixture
def fake_player():
    """Fake MPRIS player live on the session bus; skips when no bus."""
    if _IMPORT_ERROR is not None:
        pytest.skip(f"dbus-next required: {_IMPORT_ERROR}")
    fp = FakePlayer()
    fp._thread.start()
    if not fp._ready.wait(10):
        pytest.skip("session bus unresponsive (fake player never ready)")
    if fp._err:
        pytest.skip(f"session bus required: {fp._err[0]}")
    fp.reset()
    yield fp
    fp._stop.set()
    fp._thread.join(10)


def music(op: str, **kw: object):
    """Drive the fake through the real handler path (pinned player)."""
    return handle_music({"op": op, "player": BUS_NAME, **kw})
