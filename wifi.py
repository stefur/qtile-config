"""Requires Nerd fonts"""
from __future__ import annotations

from typing import TYPE_CHECKING

import asyncio

from dbus_next.aio import MessageBus
from dbus_next.constants import BusType


from libqtile.widget import base

from colors import colors

if TYPE_CHECKING:
    from typing import Dict, Any


PROPS_IFACE = "net.connman.Manager"
CONNMAN_SERVICE = "net.connman"
CONNMAN_INTERFACE = "net.connman.Manager"
CONNMAN_PATH = "/"
CONNMAN_BUS = BusType.SYSTEM


class Wifi(base._TextBox):
    """Displaying a battery icon and percentage"""

    def __init__(self, **config):
        base._TextBox.__init__(self, **config)
        self.bus = None
        self.connman = None

    async def _config_async(self):
        await self._setup_dbus()

    async def _setup_dbus(self):
        # Set up connection to DBus
        self.bus = await MessageBus(bus_type=CONNMAN_BUS).connect()
        introspection = await self.bus.introspect(CONNMAN_SERVICE, CONNMAN_PATH)
        proxy_object = self.bus.get_proxy_object(
            CONNMAN_SERVICE, CONNMAN_PATH, introspection
        )

        props = proxy_object.get_interface(PROPS_IFACE)
        props.on_property_changed(self.connman_change)

        self.connman = proxy_object.get_interface(CONNMAN_INTERFACE)

        self.configured = await self._update_wifi_info()

    def connman_change(self, interface, changed):
        """Update the charging status"""
        del interface, changed
        asyncio.create_task(self._update_wifi_info())

    async def _update_wifi_info(self):
        try:
            wifi_info = await self.connman.call_get_services()
            status = wifi_info[0][1]["State"].value
        except IndexError:
            status = None

        if status == "online":
            wifi_icon = "直"
            ssid = wifi_info[0][1]["Name"].value
        else:
            wifi_icon = "睊"
            ssid = "Disconnected"

        self.qtile.call_soon(self.bar.draw)
        self.text = f"{wifi_icon}  <span foreground='{colors['text']}'>{ssid}</span>"
