"""Requires Nerd fonts"""
from __future__ import annotations

from typing import TYPE_CHECKING

import asyncio

from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType

from libqtile import widget

from colors import colors

if TYPE_CHECKING:
    from typing import Any
    from dbus_next.signature import Variant
    from dbus_next.aio.proxy_object import ProxyInterface, ProxyObject
    from dbus_next.introspection import Node


BATTERY = "/org/freedesktop/UPower/devices/battery_BAT0"
PROPS_IFACE = "org.freedesktop.DBus.Properties"
UPOWER_SERVICE = "org.freedesktop.UPower"
UPOWER_INTERFACE = "org.freedesktop.UPower"
UPOWER_PATH = "/org/freedesktop/UPower"
UPOWER_DEVICE = UPOWER_INTERFACE + ".Device"
UPOWER_BUS = BusType.SYSTEM

battery_level_icons: dict[str, int] = {
    "\uf578": 95,
    "\uf581": 90,
    "\uf580": 80,
    "\uf57f": 70,
    "\uf57e": 60,
    "\uf57d": 50,
    "\uf57c": 40,
    "\uf57b": 30,
    "\uf57a": 20,
    "\uf579": 10,
    "\uf58d": 0,
}


class CustomBattery(widget.TextBox):
    """Displaying a battery icon and percentage"""

    def __init__(self, **config) -> None:
        widget.TextBox.__init__(self, **config)

        self.battery_status: dict[str, Any] | None
        self.battery_device: ProxyInterface
        self.upower: ProxyInterface
        self.bus: MessageBus
        self.charging: bool = False
        self.show_text: bool = False
        self.text: str

    async def _config_async(self) -> None:
        await self._setup_dbus()

    async def _setup_dbus(self) -> None:
        # Set up connection to DBus
        self.bus = await MessageBus(bus_type=UPOWER_BUS).connect()
        introspection: Node = await self.bus.introspect(UPOWER_SERVICE, UPOWER_PATH)
        proxy_object: ProxyObject = self.bus.get_proxy_object(
            UPOWER_SERVICE, UPOWER_PATH, introspection
        )

        props: ProxyInterface = proxy_object.get_interface(PROPS_IFACE)
        props.on_properties_changed(self.upower_change)  # type: ignore

        self.upower = proxy_object.get_interface(UPOWER_INTERFACE)

        # Get battery details from DBus
        self.battery_status = await self.get_battery()

        # Is laptop charging?
        self.charging = not await self.upower.get_on_battery()  # type: ignore

        await self._update_battery_info()

    async def get_battery(self) -> None:
        """Get the device and fetch its info"""

        introspection = await self.bus.introspect(UPOWER_SERVICE, BATTERY)
        battery_obj = self.bus.get_proxy_object(UPOWER_SERVICE, BATTERY, introspection)
        self.battery_device = battery_obj.get_interface(UPOWER_DEVICE)
        props = battery_obj.get_interface(PROPS_IFACE)

        # Listen for change signals on DBus
        props.on_properties_changed(self.battery_change)  # type: ignore

        await self._update_battery_info()

    def upower_change(
        self, interface: str, changed: dict[str, Variant], invalidated: list[Any]
    ) -> None:
        """Update the charging status"""
        del interface, changed, invalidated
        asyncio.create_task(self._upower_change())

    async def _upower_change(self) -> None:
        self.charging = not await self.upower.get_on_battery()  # type: ignore
        asyncio.create_task(self._update_battery_info())

    def battery_change(
        self, interface: str, changed: dict[str, Variant], invalidated: list[Any]
    ) -> None:
        """The batteries are polled every 2 mins by DBus"""
        del interface, changed, invalidated
        asyncio.create_task(self._update_battery_info())

    def toggle_text(self) -> None:
        """Show or hide the percentage next to the icon"""
        if self.show_text:
            self.show_text = False
        else:
            self.show_text = True

        asyncio.create_task(self._update_battery_info())

    async def _update_battery_info(self) -> None:
        percentage = await self.battery_device.get_percentage()  # type: ignore
        battery_icon = next(
            iter({k: v for k, v in battery_level_icons.items() if percentage >= v})
        )

        if self.charging and percentage == 100:
            battery_icon = battery_icon + "\uf492"
        elif self.charging:
            battery_icon = battery_icon + "\uf0e7"

        if self.show_text:
            result = f"{battery_icon} <span foreground='{colors['text']}'>{round(percentage)}%</span>"

        else:
            result = f"{battery_icon}"

        self.qtile.call_soon(self.bar.draw)
        self.text = result
