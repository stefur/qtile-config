"""A custom widget to show what Spotify is playing. Requires Nerd fonts."""
from __future__ import annotations

from typing import TYPE_CHECKING

import asyncio

from dbus_next import Message
from dbus_next.aio import MessageBus
from dbus_next.constants import BusType, MessageType

from libqtile.widget import base
from libqtile.utils import logger

from colors import colors

if TYPE_CHECKING:
    from typing import Dict, Any, Union, List, Optional
    from dbus_next.signature import Variant
    from dbus_next.aio.proxy_object import ProxyInterface, ProxyObject
    from dbus_next.introspection import Node

SPOTIFY_SERVICE = "org.mpris.MediaPlayer2.spotify"
SPOTIFY_INTERFACE = "org.freedesktop.DBus.Properties"
SPOTIFY_PATH = "/org/mpris/MediaPlayer2"
DBUS_PATH = "/org/freedesktop/DBus"
DBUS_INTERFACE = "org.freedesktop.DBus"
SESSION_BUS = BusType.SESSION


class NowPlaying(base._TextBox):
    """Basically set up a listener for Spotify according to my liking"""

    def __init__(self, **config) -> None:
        base._TextBox.__init__(self, **config)

        self.bus: MessageBus
        self.messagebody: List[Any] = []
        self.now_playing: Optional[str] = None
        self.playback_icon: Optional[str] = None
        self.properties_changed: Optional[Message] = None
        self.name_owner_changed: Optional[Message] = None

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
                    f"type='signal',sender='{SPOTIFY_SERVICE}',member='PropertiesChanged',path='{SPOTIFY_PATH}',interface='{SPOTIFY_INTERFACE}'"
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

        # Only listen to signal messages
        if updatemessage.message_type != MessageType.SIGNAL:
            return

        # Attempt to skip repeated signals
        if updatemessage.body == self.messagebody:
            return

        if updatemessage.member == "PropertiesChanged":
            self.spotify_changed(*updatemessage.body)
            self.messagebody = updatemessage.body

        if (
            updatemessage.member == "NameOwnerChanged"
            and SPOTIFY_SERVICE in updatemessage.body[0]
        ):
            self.spotify_nameowner(*updatemessage.body)
            self.messagebody = updatemessage.body

    def spotify_changed(
        self, interface: str, changed: Dict[str, Variant], invalidated: List[Any]
    ) -> None:
        """Send the properties if an update is received, e.g. new song or playback status"""
        del interface, invalidated
        metadata = changed.get("Metadata")
        metadata = metadata.value  # type: ignore
        playbackstatus = changed.get("PlaybackStatus")
        playbackstatus = playbackstatus.value  # type: ignore
        asyncio.create_task(self.update_widget(metadata, playbackstatus))

    def spotify_nameowner(self, name: str, old_owner: str, new_owner: str) -> None:
        """If the nameowner for Spotify changed we assume it has closed and clear the text in the widget"""
        del name, old_owner, new_owner
        self.qtile.call_soon(self.bar.draw)
        self.text = ""

    async def update_widget(
        self, metadata: Optional[Variant], playbackstatus: Optional[Variant]
    ) -> None:
        """Update song artist and title, including playback status"""

        artist = metadata["xesam:artist"].value[0]  # type: ignore
        song = metadata["xesam:title"].value  # type: ignore
        self.now_playing = f"{artist} - {song}"
        self.now_playing.replace("\n", "")

        if len(self.now_playing) > 35:
            self.now_playing = self.now_playing[:35]
            self.now_playing += "…"
            if "(" in self.now_playing and ")" not in self.now_playing:
                self.now_playing += ")"

        if playbackstatus == "Paused":
            self.playback_icon = f"<span foreground='{colors['primary']}'> \
                                 </span>"

        elif playbackstatus == "Playing":
            self.playback_icon = f"<span foreground='{colors['primary']}'> \
                                契 </span>"
        if self.text != self.now_playing:
            self.qtile.call_soon(self.bar.draw)
            self.text = f"{self.playback_icon} {self.now_playing}"
