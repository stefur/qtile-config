"""Requires Nerd fonts"""

import subprocess
import re

from libqtile.utils import send_notification
from libqtile.widget import base
from libqtile.log_utils import logger

from colors import colors

class CustomBattery(base.ThreadPoolText):
    """Displaying a battery icon and percentage"""

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("update_interval", 15, "Update time in seconds.")
    ]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(CustomBattery.defaults)

        self.find_battery_level = re.compile(r'\, (\d?\d?\d?)%')

        self.battery_level_icons = {
            "":95,
            "":90,
            "":80,
            "":70,
            "":60,
            "":50,
            "":40,
            "":30,
            "":20,
            "":10,
            "":0
        }

        self.text = self.poll()

    def poll(self):
        """Get the status from ACPI, return the corresponding icon"""

        battery = subprocess.check_output(['acpi'], shell=True).decode('utf-8')
        battery_level = int(self.find_battery_level.search(battery).groups()[0])

        if re.search(r"Discharging", battery):
            battery_icon = { k:v for k, v in self.battery_level_icons.items() if battery_level > v}
            battery_icon = next(iter(battery_icon))
        elif re.search(r"Charging", battery):
            battery_icon = ""
        elif re.search(r"Not charging", battery):
            battery_icon = ""
        else:
            logger.error("Cannot determine battery status. Is ACPI installed and working?")

        output = "".join([battery_icon, ' <span foreground="', colors['text'], '">', "{0}%".format(battery_level), '</span>'])

        return output
