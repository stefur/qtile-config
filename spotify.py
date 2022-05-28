"""A custom widget to show what Spotify is playing. Requires Nerd fonts."""
from __future__ import annotations

from typing import TYPE_CHECKING

import asyncio
from dbus_next.aio.proxy_object import ProxyInterface, ProxyObject

from dbus_next.message import Message
from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType, MessageType

from libqtile import widget
from libqtile.log_utils import logger

from colors import colors

if TYPE_CHECKING:
    from typing import Any, Optional
    from dbus_next.signature import Variant
    from dbus_next.introspection import Node

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

        if (
            updatemessage.member == "NameOwnerChanged"
            and SPOTIFY_SERVICE in updatemessage.body[0]
        ):
            asyncio.create_task(self.spotify_nameowner(*updatemessage.body))

        elif (
            updatemessage.member == "PropertiesChanged"
            and list(updatemessage.body[1].keys())[0] == "PlaybackStatus"
        ):
            asyncio.create_task(self.playback_changed())

        elif (
            "spotify" in updatemessage.body[1]["Metadata"].value["mpris:trackid"].value
        ):
            asyncio.create_task(self.metadata_changed(*updatemessage.body))

    async def get_proxy_interface(self) -> ProxyInterface:
        """Get the proxy interface"""
        introspection: Node = await self.bus.introspect(SPOTIFY_SERVICE, SPOTIFY_PATH)
        proxy_object: ProxyObject = self.bus.get_proxy_object(
            SPOTIFY_SERVICE, SPOTIFY_PATH, introspection
        )

        proxy_interface: ProxyInterface = proxy_object.get_interface(
            "org.mpris.MediaPlayer2.Player"
        )

        return proxy_interface

    async def get_playback_status(self) -> None:
        """Get the playback status from Spotify"""

        try:
            proxy_interface: ProxyInterface = await self.get_proxy_interface()
        except Exception:
            return

        playback_status: str = await proxy_interface.get_playback_status()  # type: ignore

        if playback_status == "Paused":
            self.playback_icon = f"<span foreground='{colors['primary']}'> \
                                \uf8e3</span>"

        elif playback_status == "Playing":
            self.playback_icon = f"<span foreground='{colors['primary']}'> \
                                \uf909</span>"

    async def get_metadata(self) -> None:
        """Get the metadata from Spotify"""
        try:
            proxy_interface: ProxyInterface = await self.get_proxy_interface()
        except Exception:
            return

        metadata: dict[str, Variant] = await proxy_interface.get_metadata()  # type: ignore

        await self.unpack_metadata(metadata)

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

    async def metadata_changed(
        self, interface: str, changed: dict[str, Variant], invalidated: list[Any]
    ) -> None:
        """Update the song info in the widget"""
        del interface, invalidated  # Unused parameters

        await self.unpack_metadata(changed["Metadata"].value)

        await self.get_playback_status()

        await self.update_bar()

    async def playback_changed(self) -> None:
        """Update the playback icon in the widget"""
        await self.get_playback_status()

        await self.get_metadata()

        await self.update_bar()

    async def update_bar(self) -> None:
        """Update the bar with new info"""
        if self.now_playing is None or self.now_playing == "":
            return

        self.qtile.call_soon(self.bar.draw)
        self.text = f"{self.playback_icon} {self.now_playing}"

    async def spotify_nameowner(
        self, name: str, old_owner: str, new_owner: str
    ) -> None:
        """If the nameowner for Spotify changed we assume it has closed and clear the text in the widget"""
        del name, old_owner, new_owner  # Unused parameters
        self.qtile.call_soon(self.bar.draw)
        self.text = ""
