"""I want to use battery icons updated with Font Awesome"""

import subprocess
import re

from libqtile.utils import send_notification
from libqtile.widget import base
from libqtile.log_utils import logger

import fontawesome as fa

from colors import colors

class CustomBattery(base.ThreadPoolText):
    """Showing battery icon the way I want"""

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('low_foreground', 'FF0000', 'Font color on low battery'),
        ("update_interval", 15, "Update time in seconds.")
    ]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(CustomBattery.defaults)

        self.find_battery_level = re.compile(r'\, (\d?\d?\d?)%')

        self.notification_sent = False

        self.text = self.poll()

    def poll(self):
        """Get the status from ACPI, e.g. discharging or charging"""

        battery = subprocess.check_output(['acpi'], shell=True).decode('utf-8')

        if re.search(r"Discharging", battery):
            self.battery_status = "Discharging"
            self.status_icon = ""
        elif re.search(r"Charging", battery):
            self.battery_status = "Charging"
            self.status_icon = "  " + fa.icons['bolt']
            self.notification_sent = False
        elif re.search(r"Not charging", battery):
            self.battery_status = "Not charging"
            self.status_icon = "  " + fa.icons['plug']
            self.notification_sent = False
            self.foreground = colors['text']
        else:
            logger.error("Cannot determine battery status. Is ACPI installed and working?")

        self.battery_level = self.find_battery_level.search(battery)
        self.battery_level = int(self.battery_level.groups()[0])

        if self.battery_level >= 75:
            self.battey_icon = fa.icons['battery-full']
        elif self.battery_level >= 50:
            self.battery_icon = fa.icons['battery-three-quarters']
        elif self.battery_level >= 25:
            self.battery_icon = fa.icons['battery-half']
        elif self.battery_level > 10:
            self.battery_icon = fa.icons['battery-quarter']
        elif self.battery_level <= 10:
            self.battery_icon = fa.icons['battery-empty']
            if self.battery_status == "Charging":
                self.foreground = colors['text']
            else:
                self.foreground = self.low_foreground
            if not self.notification_sent:
                send_notification("Warning", "Battery at {0}%".format(self.battery_level), urgent=True)
                self.notification_sent = True

        self.output = self.battery_icon + self.status_icon

        return self.output
