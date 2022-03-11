"""Requires Nerd fonts"""
from __future__ import annotations

from typing import TYPE_CHECKING

import asyncio

from dbus_next.aio import MessageBus
from dbus_next.constants import BusType


from libqtile.widget import base

from colors import colors

if TYPE_CHECKING:
    from typing import Dict, List, Any, Union
    from dbus_next.signature import Variant
    from dbus_next.aio.proxy_object import ProxyInterface, ProxyObject
    from dbus_next.introspection import Node


CONNMAN_SERVICE = "net.connman"
CONNMAN_INTERFACE = "net.connman.Manager"
CONNMAN_PATH = "/"
CONNMAN_BUS = BusType.SYSTEM


class Wifi(base._TextBox):
    """Displaying a wifi icon and ssid"""

    def __init__(self, **config) -> None:
        base._TextBox.__init__(self, **config)
        self.add_callbacks(
            {
                "Button3": self.cmd_toggle_ssid,
            }
        )
        self.bus: MessageBus
        self.connman: ProxyInterface
        self.show_ssid: bool = False

    async def _config_async(self) -> None:
        await self._setup_dbus()

    async def _setup_dbus(self) -> None:
        self.bus = await MessageBus(bus_type=CONNMAN_BUS).connect()
        introspection: Node = await self.bus.introspect(CONNMAN_SERVICE, CONNMAN_PATH)
        proxy_object: ProxyObject = self.bus.get_proxy_object(
            CONNMAN_SERVICE, CONNMAN_PATH, introspection
        )

        self.connman = proxy_object.get_interface(CONNMAN_INTERFACE)
        self.connman.on_property_changed(self.connman_change)  # type: ignore

        await self.update_wifi_info()

    def connman_change(self, interface: str, changed: Dict[str, Variant]) -> None:
        """Listen to wifi changes"""
        del interface, changed
        asyncio.create_task(self.update_wifi_info())

    def cmd_toggle_ssid(self) -> None:
        """Show or hide the ssid next to the icon"""
        if self.show_ssid:
            self.show_ssid = False
        else:
            self.show_ssid = True

        asyncio.create_task(self.update_wifi_info())

    async def update_wifi_info(self) -> None:
        """Update the info in the widget"""
        wifi_info: List[List[Dict[str, Variant]]] = await self.connman.call_get_services()  # type: ignore
        if not wifi_info:
            status = None
        else:
            status = wifi_info[0][1]["State"].value

        if status == "online":
            wifi_icon = "直"
            ssid = wifi_info[0][1]["Name"].value
        else:
            wifi_icon = "睊"
            ssid = "Disconnected"

        if self.show_ssid:
            result = f"{wifi_icon}  <span foreground='{colors['text']}'>{ssid}</span>"

        else:
            result = f"{wifi_icon}"

        self.qtile.call_soon(self.bar.draw)
        self.text = result
