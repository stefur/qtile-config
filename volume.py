"""No polling, get the volume upon change"""
from __future__ import annotations

import subprocess
import re
from libqtile import widget
from libqtile.command.base import expose_command
from colors import colors

volume_level_icons: dict[str, int] = {"󰕾": 66, "󰖀": 33, "󰕿": 0}


class VolumeCtrl(widget.TextBox):
    """Use pactl to get the volume, transform it to a readable format and return an icon"""

    def __init__(self, **config):
        widget.TextBox.__init__(self, **config)

        self.show_text: bool = False
        self.find_value = re.compile(r"(\d?\d?\d?)%")
        self.volume, self.icon = self.get_volume()

        self.update_widget()

    def get_volume(self) -> tuple[int, str]:
        """Get the volume value"""

        try:
            cmd_output = subprocess.check_output(
                ["pactl get-sink-volume 0"], shell=True
            ).decode("utf-8")
            mute = subprocess.check_output(
                ["pactl get-sink-mute 0"], shell=True
            ).decode("utf-8")

            volume = int(self.find_value.search(cmd_output).groups()[0])  # type: ignore

        except subprocess.CalledProcessError:
            volume = 0
            mute = "no"

        icon = next(iter({k: v for k, v in volume_level_icons.items() if volume >= v}))

        if re.search("yes", mute):
            icon = "󰸈"
        return volume, icon

    def update_widget(self) -> None:
        """Update the widget"""
        if self.show_text:
            self.text = f"{self.icon} <span foreground='{colors['text']}'>{self.volume}%</span>"
        else:
            self.text = f"{self.icon}"

        #FIXME: very unclear why this try statement is neeeded upon init.
        try:
            self.bar.draw()
        except AttributeError:
            return None

    @expose_command()
    def adjust_volume(self, option: str) -> None:
        """Adjust the volume and refresh volume and icon"""

        match option:
            case "increase":
                if self.volume is not None and self.volume < 100:
                    subprocess.call(["pactl set-sink-volume 0 +5%"], shell=True)

            case "decrease":
                subprocess.call(["pactl set-sink-volume 0 -5%"], shell=True)

            case "mute":
                subprocess.call(["pactl set-sink-mute 0 toggle"], shell=True)

        self.volume, self.icon = self.get_volume()
        self.update_widget()


    @expose_command()
    def toggle_text(self) -> None:
        """Show or hide the percentage next to the icon"""
        if self.show_text:
            self.show_text = False
        else:
            self.show_text = True

        self.update_widget()
