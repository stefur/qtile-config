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

        self.add_callbacks(
            {
                "Button1": self.mute,
                "Button3": self.toggle_text,
                "Button4": self.increase_vol,
                "Button5": self.decrease_vol,
            }
        )

        self.show_text: bool = False
        self.find_value = re.compile(r"(\d?\d?\d?)%")
        self.volume: int | None = self.get_vol()

    def get_vol(self) -> int | None:
        """Get the volume value"""

        try:
            output = subprocess.check_output(
                ["pactl get-sink-volume 0"], shell=True
            ).decode("utf-8")
            mute = subprocess.check_output(
                ["pactl get-sink-mute 0"], shell=True
            ).decode("utf-8")
            vol = int(self.find_value.search(output).groups()[0])  # type: ignore
            icon = next(iter({k: v for k, v in volume_level_icons.items() if vol >= v}))

            if re.search("yes", mute):
                icon = "󰸈"

            if self.show_text:
                self.text = f"{icon} <span foreground='{colors['text']}'>{vol}%</span>"
            else:
                self.text = f"{icon}"

            self.bar.draw()

            return vol
        except AttributeError:
            return None

    @expose_command()
    def increase_vol(self) -> None:
        """Increase the volume and refresh volume and icon"""

        if self.volume is not None and self.volume < 100:
            subprocess.call(["pactl set-sink-volume 0 +5%"], shell=True)
            self.volume = self.get_vol()

    @expose_command()
    def decrease_vol(self) -> None:
        """Decrease the volume and refresh volume and icon"""

        subprocess.call(["pactl set-sink-volume 0 -5%"], shell=True)
        self.volume = self.get_vol()

    @expose_command()
    def mute(self) -> None:
        """Toggle to mute/unmute volume and refresh icon"""

        subprocess.call(["pactl set-sink-mute 0 toggle"], shell=True)
        self.volume = self.get_vol()

    def toggle_text(self) -> None:
        """Show or hide the percentage next to the icon"""
        if self.show_text:
            self.show_text = False
        else:
            self.show_text = True

        self.volume = self.get_vol()
