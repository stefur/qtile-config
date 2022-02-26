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


BATTERY = "/org/freedesktop/UPower/devices/battery_BAT0"
PROPS_IFACE = "org.freedesktop.DBus.Properties"
UPOWER_SERVICE = "org.freedesktop.UPower"
UPOWER_INTERFACE = "org.freedesktop.UPower"
UPOWER_PATH = "/org/freedesktop/UPower"
UPOWER_DEVICE = UPOWER_INTERFACE + ".Device"
UPOWER_BUS = BusType.SYSTEM

battery_level_icons: Dict[str, int] = {
    "": 95,
    "": 90,
    "": 80,
    "": 70,
    "": 60,
    "": 50,
    "": 40,
    "": 30,
    "": 20,
    "": 10,
    "": 0,
}


class CustomBattery(base._TextBox):
    """Displaying a battery icon and percentage"""

    def __init__(self, **config):
        base._TextBox.__init__(self, **config)

        self.battery_status = None
        self.battery_dev = None
        self.upower = None
        self.bus = None
        self.charging: bool = False

    async def _config_async(self):
        await self._setup_dbus()

    async def _setup_dbus(self):
        # Set up connection to DBus
        self.bus = await MessageBus(bus_type=UPOWER_BUS).connect()
        introspection = await self.bus.introspect(UPOWER_SERVICE, UPOWER_PATH)
        proxy_object = self.bus.get_proxy_object(
            UPOWER_SERVICE, UPOWER_PATH, introspection
        )

        props = proxy_object.get_interface("org.freedesktop.DBus.Properties")
        props.on_properties_changed(self.upower_change)

        self.upower = proxy_object.get_interface(UPOWER_INTERFACE)

        # Get battery details from DBus
        self.battery_status: Dict[str, Any] = await self.get_battery()

        # Is laptop charging?
        self.charging: bool = not await self.upower.get_on_battery()

        self.configured = await self._update_battery_info()

    async def get_battery(self):
        """Get the device and fetch its info"""

        introspection = await self.bus.introspect(UPOWER_SERVICE, BATTERY)
        battery_obj = self.bus.get_proxy_object(UPOWER_SERVICE, BATTERY, introspection)
        self.battery_dev = battery_obj.get_interface(UPOWER_DEVICE)
        props = battery_obj.get_interface(PROPS_IFACE)

        # Listen for change signals on DBus
        props.on_properties_changed(self.battery_change)

        await self._update_battery_info()

    def upower_change(self, interface, changed, invalidated):
        """Update the charging status"""
        del interface, changed, invalidated
        asyncio.create_task(self._upower_change())

    async def _upower_change(self):
        self.charging = not await self.upower.get_on_battery()
        asyncio.create_task(self._update_battery_info())

    def battery_change(self, interface, changed, invalidated):
        """The batteries are polled every 2 mins by DBus"""
        del interface, changed, invalidated
        asyncio.create_task(self._update_battery_info())

    async def _update_battery_info(self):
        percentage = await self.battery_dev.get_percentage()
        if self.charging and percentage == 100:
            battery_icon = ""
        elif self.charging:
            battery_icon = ""
        else:
            battery_icon = next(
                iter({k: v for k, v in battery_level_icons.items() if percentage >= v})
            )

        self.qtile.call_soon(self.bar.draw)
        self.text = f"{battery_icon} <span foreground='{colors['text']}'>{round(percentage)}%</span>"
