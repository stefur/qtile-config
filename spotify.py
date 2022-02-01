"""A custom widget to show what Spotify is playing, based on mpris2 widget. Requires Nerd fonts."""
from dbus_next.constants import MessageType  # type: ignore

from libqtile.log_utils import logger
from libqtile.utils import add_signal_receiver
from libqtile.widget import base
from colors import colors


class NowPlaying(base._TextBox):
    """Basically set up a listener for Spotify according to my liking"""

    def __init__(self, **config):
        base._TextBox.__init__(self, **config)

        self.statusicon = ""
        self.displaytext = ""
        self.display_metadata = ["xesam:artist", "xesam:title"]

    async def _config_async(self):

        subscribe_update = await add_signal_receiver(
            self.updatemessage,
            session_bus=True,
            signal_name="PropertiesChanged",
            bus_name="org.mpris.MediaPlayer2.spotify",
            path="/org/mpris/MediaPlayer2",
            dbus_interface="org.freedesktop.DBus.Properties",
        )

        if not subscribe_update:
            msg = "Unable to add signal receiver for Spotify."
            logger.warning(msg)

        subscribe_closed = await add_signal_receiver(
            self.closemessage,
            session_bus=True,
            signal_name="NameOwnerChanged",
            path="/org/freedesktop/DBus",
            dbus_interface="org.freedesktop.DBus",
        )

        if not subscribe_closed:
            msg = "Unable to add signal receiver for when Spotify is closed."
            logger.warning(msg)

    def updatemessage(self, updatemessage):
        """Send the properties if an update is received, e.g. new song or playback status"""

        if updatemessage.message_type != MessageType.SIGNAL:
            return

        self.update(*updatemessage.body)

    def closemessage(self, closemessage):
        """Send the message that Spotify has been closed"""
        if closemessage.message_type != MessageType.SIGNAL:
            return

        self.closed(*closemessage.body)

    def closed(self, name, old_owner, new_owner):
        """If Spotify is closed, clear the text in the widget"""

        del new_owner
        if name == "org.mpris.MediaPlayer2.spotify" and old_owner:
            self.text = ""
            self.bar.draw()

    def update(self, interface_name, changed_properties, _invalidated_properties):
        """Update song artist and title, including playback status"""

        del interface_name
        metadata = changed_properties.get("Metadata")
        if metadata:
            metadata = metadata.value

            meta_list = []
            for key in self.display_metadata:
                val = getattr(metadata.get(key), "value", None)
                if isinstance(val, str):
                    meta_list.append(val)
                elif isinstance(val, list):
                    val = " - ".join((y for y in val if isinstance(y, str)))
                    meta_list.append(val)

            self.displaytext = " - ".join(meta_list)
            self.displaytext.replace("\n", "")
            if len(self.displaytext) > 35:
                self.displaytext = self.displaytext[:35]
                self.displaytext += " ..."
                if ("(" in self.displaytext) and (")" not in self.displaytext):
                    self.displaytext += ")"

        playbackstatus = getattr(
            changed_properties.get("PlaybackStatus"), "value", None
        )
        if playbackstatus == "Paused":
            self.statusicon = f"<span foreground='{colors['primary']}'> \
                                 </span>"

        elif playbackstatus == "Playing":
            self.statusicon = f"<span foreground='{colors['primary']}'> \
                                契 </span>"
        elif self.displaytext:
            # Spotify usually send more than one "Playing" message.
            pass

        if self.text != self.displaytext:
            self.text = self.statusicon + self.displaytext
            self.bar.draw()
