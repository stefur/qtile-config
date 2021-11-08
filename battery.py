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
        ("update_interval", 15, "Update time in seconds.")
    ]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(CustomBattery.defaults)

        self.add_callbacks({
            'Button3': self.toggle_percentage,
        })

        self.find_battery_level = re.compile(r'\, (\d?\d?\d?)%')

        self.notification_sent = False

        self.display_percentage = False

        self.text = self.poll()

    def toggle_percentage(self):

        if not self.display_percentage:
            self.display_percentage = True
            self.text = self.poll()
            self.bar.draw()
        elif self.display_percentage:
            self.display_percentage = False
            self.text = self.poll()
            self.bar.draw()

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
            self.battery_icon = fa.icons['battery-full']
            self.foreground = colors['text']
        elif self.battery_level >= 50:
            self.battery_icon = fa.icons['battery-three-quarters']
            self.foreground = colors['text']
        elif self.battery_level >= 25:
            self.battery_icon = fa.icons['battery-half']
            self.foreground = colors['text']
        elif self.battery_level > 10:
            self.battery_icon = fa.icons['battery-quarter']
            self.foreground = colors['text']
        elif self.battery_level <= 10:
            self.battery_icon = fa.icons['battery-empty']
            if self.battery_status == "Charging":
                self.foreground = colors['text']
            else:
                self.foreground = colors['urgent']
            if not self.notification_sent:
                send_notification("Warning", "Battery at {0}%".format(self.battery_level), urgent=True)
                self.notification_sent = True

        if self.display_percentage:
            self.percentage = "{0}%  ".format(self.battery_level)
        if not self.display_percentage:
            self.percentage = ""

        self.output = self.percentage + self.battery_icon + self.status_icon

        return self.output
