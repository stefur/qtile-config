"""A custom widget to show what Spotify is playing. Requires Nerd fonts."""
from __future__ import annotations

from typing import TYPE_CHECKING

import asyncio
import psutil  # type: ignore

from dbus_next.message import Message
from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType, MessageType

from libqtile import widget
from libqtile.log_utils import logger

from colors import colors

if TYPE_CHECKING:
    from typing import Any, Optional
    from dbus_next.signature import Variant

SPOTIFY_SERVICE = "org.mpris.MediaPlayer2.spotify"
SPOTIFY_INTERFACE = "org.freedesktop.DBus.Properties"
SPOTIFY_PATH = "/org/mpris/MediaPlayer2"
DBUS_PATH = "/org/freedesktop/DBus"
DBUS_INTERFACE = "org.freedesktop.DBus"
SESSION_BUS = BusType.SESSION


class Spotify(widget.TextBox):
    """Basically set up a listener for Spotify according to my liking"""

    def __init__(self, **config) -> None:
        widget.TextBox.__init__(self, **config)

        self.bus: MessageBus
        self.now_playing: Optional[str] = None
        self.playback_icon: Optional[str] = None
        self.properties_changed: Optional[Message] = None
        self.name_owner_changed: Optional[Message] = None
        self.text: str

    async def _config_async(self) -> None:
        await self._setup_dbus()

    async def _setup_dbus(self) -> None:
        self.bus = await MessageBus(bus_type=SESSION_BUS).connect()

        self.properties_changed = await self.bus.call(
            Message(
                message_type=MessageType.METHOD_CALL,
                destination="org.freedesktop.DBus",
                interface="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                member="AddMatch",
                signature="s",
                body=[
                    f"type='signal',member='PropertiesChanged',path='{SPOTIFY_PATH}',interface='{SPOTIFY_INTERFACE}'"
                ],
            )
        )

        self.name_owner_changed = await self.bus.call(
            Message(
                message_type=MessageType.METHOD_CALL,
                destination="org.freedesktop.DBus",
                interface="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                member="AddMatch",
                signature="s",
                body=[
                    f"type='signal',sender='{DBUS_INTERFACE}',member='NameOwnerChanged',path='{DBUS_PATH}',interface='{DBUS_INTERFACE}'"
                ],
            )
        )

        if not self.properties_changed or not self.name_owner_changed:
            logger.error("Failed to send messages with AddMatch to DBus")

        self.bus.add_message_handler(self.message_handler)

    def message_handler(self, updatemessage: Message) -> None:
        """Send the properties if an update is received, e.g. new song or playback status"""

        # TODO: Come up with a better solution to prevent other players from affecting the widget.

        if (
            updatemessage.member == "NameOwnerChanged"
            and SPOTIFY_SERVICE in updatemessage.body[0]
        ):
            asyncio.create_task(self.spotify_nameowner(*updatemessage.body))

        # Check if Spotify is running, otherwise do nothing.
        elif "spotify" not in (i.name() for i in psutil.process_iter()):
            return

        # Playback status will still be affected by other players sending a signal, such as Youtube.
        elif (
            updatemessage.member == "PropertiesChanged"
            and list(updatemessage.body[1].keys())[0] == "PlaybackStatus"
        ):
            asyncio.create_task(self.playback_changed(*updatemessage.body))

        # Check if the metadata trackid actually contains "spotify" to prevent other signals to update metadata (again, Youtube).
        elif (
            "spotify"
            not in updatemessage.body[1]["Metadata"].value["mpris:trackid"].value
        ):
            return

        elif (
            updatemessage.member == "PropertiesChanged"
            and list(updatemessage.body[1].keys())[0] == "Metadata"
        ):
            asyncio.create_task(self.metadata_changed(*updatemessage.body))

    async def metadata_changed(
        self, interface: str, changed: dict[str, Variant], invalidated: list[Any]
    ) -> None:
        """Update the song info in the widget"""
        del interface, invalidated  # Unused parameters

        artist = changed["Metadata"].value["xesam:artist"].value[0]
        song = changed["Metadata"].value["xesam:title"].value
        self.now_playing = f"{artist} - {song}"
        self.now_playing.replace("\n", "")

        if len(self.now_playing) > 35:
            self.now_playing = self.now_playing[:35]
            self.now_playing += "…"
            if "(" in self.now_playing and ")" not in self.now_playing:
                self.now_playing += ")"

        self.now_playing = self.now_playing.replace("&", "&amp;")

        self.qtile.call_soon(self.bar.draw)
        self.text = f"{self.playback_icon} {self.now_playing}"

    async def playback_changed(
        self, interface: str, changed: dict[str, Variant], invalidated: list[Any]
    ) -> None:
        """Update the playback icon in the widget"""
        del interface, invalidated  # Unused parameters

        if changed["PlaybackStatus"].value == "Paused":
            self.playback_icon = f"<span foreground='{colors['primary']}'> \
                                \uf8e3</span>"

        elif changed["PlaybackStatus"].value == "Playing":
            self.playback_icon = f"<span foreground='{colors['primary']}'> \
                                \uf909</span>"
        self.qtile.call_soon(self.bar.draw)
        self.text = f"{self.playback_icon} {self.now_playing}"

    async def spotify_nameowner(
        self, name: str, old_owner: str, new_owner: str
    ) -> None:
        """If the nameowner for Spotify changed we assume it has closed and clear the text in the widget"""
        del name, old_owner, new_owner  # Unused parameters
        self.qtile.call_soon(self.bar.draw)
        self.text = ""
