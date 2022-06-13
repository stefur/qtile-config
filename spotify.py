"""A custom widget to show what Spotify is playing. Requires Nerd fonts."""
from __future__ import annotations

from typing import TYPE_CHECKING

import asyncio

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
        self.spotify_id: Optional[str] = None

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

        self.spotify_id = await self.get_spotify_id()

    def message_handler(self, updatemessage: Message) -> None:
        """Send the properties if an update is received, e.g. new song or playback status"""

        if (
            updatemessage.member == "NameOwnerChanged"
            and SPOTIFY_SERVICE in updatemessage.body[0]
        ):
            asyncio.create_task(self.new_name_owner(*updatemessage.body))

        elif (
            updatemessage.sender == self.spotify_id
            and updatemessage.member == "PropertiesChanged"
        ):
            asyncio.create_task(self.update_widget(*updatemessage.body))

    async def get_spotify_id(self) -> str:
        """Get name owner ID of Spotify"""

        reply = await self.bus.call(
            Message(
                message_type=MessageType.METHOD_CALL,
                destination="org.freedesktop.DBus",
                path="/",
                interface="org.freedesktop.DBus",
                member="GetNameOwner",
                signature="s",
                body=["org.mpris.MediaPlayer2.spotify"],
            )
        )
        assert reply is not None, "This should not be None"

        if reply.message_type == MessageType.ERROR:
            raise Exception(reply.body[0])

        return reply.body[0]

    async def get_property(self, prop: str) -> Message:
        """Get a specific property"""

        reply = await self.bus.call(
            Message(
                message_type=MessageType.METHOD_CALL,
                destination="org.mpris.MediaPlayer2.spotify",
                path="/org/mpris/MediaPlayer2",
                interface="org.freedesktop.DBus.Properties",
                member="Get",
                signature="ss",
                body=["org.mpris.MediaPlayer2.Player", prop],
            )
        )
        assert reply is not None, "This should not be None"

        if reply.message_type == MessageType.ERROR:
            raise Exception(reply.body[0])

        return reply

    async def unpack_metadata(self, metadata: dict[str, Variant]) -> None:
        """Unpack the metadata to create the finished string"""
        artist = metadata["xesam:artist"].value[0]
        song = metadata["xesam:title"].value

        if artist == "" and song == "":
            return

        self.now_playing = f"{artist} - {song}"
        self.now_playing.replace("\n", "")

        if len(self.now_playing) > 35:
            self.now_playing = self.now_playing[:35]
            self.now_playing += "…"
            if "(" in self.now_playing and ")" not in self.now_playing:
                self.now_playing += ")"

        self.now_playing = self.now_playing.replace("&", "&amp;")

    async def update_widget(
        self, interface: str, changed: dict[str, Variant], invalidated: list[Any]
    ) -> None:
        """Update the song info in the widget"""
        del interface, invalidated  # Unused parameters

        message_contains: str = list(changed.keys())[0]

        if message_contains == "PlaybackStatus":
            await self.update_playback_icon(changed["PlaybackStatus"].value)

            metadata = await self.get_property("Metadata")

            await self.unpack_metadata(metadata.body[0].value)

        elif message_contains == "Metadata":
            await self.unpack_metadata(changed["Metadata"].value)

            playback_status = await self.get_property("PlaybackStatus")

            await self.update_playback_icon(playback_status.body[0].value)

        await self.update_bar()

    async def update_playback_icon(self, playback_status: str) -> None:
        """Update the playback icon in the widget"""

        if playback_status == "Paused":
            self.playback_icon = f"<span foreground='{colors['primary']}'> \
                                \uf8e3</span>"

        elif playback_status == "Playing":
            self.playback_icon = f"<span foreground='{colors['primary']}'> \
                                \uf909</span>"

    async def update_bar(self) -> None:
        """Update the bar with new info"""
        if self.now_playing is None or self.now_playing == "":
            return

        self.qtile.call_soon(self.bar.draw)
        self.text = f"{self.playback_icon} {self.now_playing}"

    async def new_name_owner(self, name: str, old_owner: str, new_owner: str) -> None:
        """Picking up whether Spotify was started or killed"""
        del name  # Unused parameter

        if new_owner != "":
            self.spotify_id = await self.get_spotify_id()
        elif old_owner != "":
            self.spotify_id = None
            self.qtile.call_soon(self.bar.draw)
            self.text = ""
