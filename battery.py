"""Requires Nerd fonts"""
from __future__ import annotations

from typing import TYPE_CHECKING

import psutil  # type: ignore

from libqtile.widget import base
from libqtile.log_utils import logger

from colors import colors

if TYPE_CHECKING:
    from typing import Dict


class CustomBattery(base.ThreadPoolText):
    """Displaying a battery icon and percentage"""

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [("update_interval", 15, "Update time in seconds.")]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(CustomBattery.defaults)

        self.battery_level_icons: Dict[str, int] = {
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

        self.text = self.poll()

    def poll(self) -> str:
        """Get the battery level, return the corresponding icon"""

        battery = psutil.sensors_battery()

        if battery.power_plugged is False:
            battery_icon = next(
                iter(
                    {
                        k: v
                        for k, v in self.battery_level_icons.items()
                        if battery.percent >= v
                    }
                )
            )
        elif battery.power_plugged is True and battery.percent == 100:
            battery_icon = ""

        elif battery.power_plugged is True:
            battery_icon = ""

        else:
            logger.error("Cannot determine battery status.")

        return f"{battery_icon} <span foreground='{colors['text']}'>{round(battery.percent)}%</span>"
