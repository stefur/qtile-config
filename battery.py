"""Requires Nerd fonts"""

import subprocess
import re

from libqtile.utils import send_notification
from libqtile.widget import base
from libqtile.log_utils import logger

from colors import colors

class CustomBattery(base.ThreadPoolText):
    """Displaying a battery icon the way I want"""

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("update_interval", 15, "Update time in seconds.")
    ]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(CustomBattery.defaults)

        self.find_battery_level = re.compile(r'\, (\d?\d?\d?)%')

        self.text = self.poll()

    def poll(self):
        """Get the status from ACPI, e.g. discharging or charging"""

        battery = subprocess.check_output(['acpi'], shell=True).decode('utf-8')

        self.battery_level = self.find_battery_level.search(battery)
        self.battery_level = int(self.battery_level.groups()[0])

        if re.search(r"Discharging", battery):
            if self.battery_level >= 95:
                self.battery_icon = ""
            elif self.battery_level >= 90:
                self.battery_icon = ""
            elif self.battery_level >= 80:
                self.battery_icon = ""
            elif self.battery_level >= 70:
                self.battery_icon = ""
            elif self.battery_level >= 60:
                self.battery_icon = ""
            elif self.battery_level >= 50:
                self.battery_icon = ""
            elif self.battery_level >= 40:
                self.battery_icon = ""
            elif self.battery_level >= 30:
                self.battery_icon = ""
            elif self.battery_level >= 20:
                self.battery_icon = ""
            elif self.battery_level >= 10:
                self.battery_icon = ""
            elif self.battery_level < 10:
                self.battery_icon = ""
                self.foreground = colors['urgent']
                if self.battery_status == "Charging":
                    self.foreground = colors['main']
                else:
                    self.foreground = colors['urgent']               
        elif re.search(r"Charging", battery):
            self.battery_icon = ""
        elif re.search(r"Not charging", battery):
            self.battery_icon = ""
        else:
            logger.error("Cannot determine battery status. Is ACPI installed and working?")

        self.output = "".join([self.battery_icon, ' <span foreground="', colors['text'], '">', "{0}%".format(self.battery_level), '</span>'])

        return self.output
