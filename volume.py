"""I don't want to poll alsa all the time but rather get the volume upon change"""
from __future__ import annotations

from typing import TYPE_CHECKING

import subprocess
import re
from libqtile import widget

from colors import colors

if TYPE_CHECKING:
    from typing import Dict

volume_level_icons: Dict[str, int] = {"墳": 66, "奔": 33, "奄": 0}


class VolumeCtrl(widget.TextBox):
    """Use amixer to get the volume, transform it to a readable format and return an icon"""

    def __init__(self, **config):
        widget.TextBox.__init__(self, **config)

        self.add_callbacks(
            {
                "Button1": self.cmd_mute,
                "Button3": self.cmd_toggle_percentage,
                "Button4": self.cmd_increase_vol,
                "Button5": self.cmd_decrease_vol,
            }
        )

        self.show_percentage: bool = False
        self.vol_value = re.compile(r"\[(\d?\d?\d?)%\]")
        self.text = self.get_vol()

    def get_vol(self) -> str:
        """Get the volume value"""
        output = subprocess.check_output(["amixer sget Master"], shell=True).decode(
            "utf-8"
        )

        vol = int(self.vol_value.search(output).groups()[0])
        icon = next(iter({k: v for k, v in volume_level_icons.items() if vol >= v}))

        if re.search("off", output):
            vol = 0
            icon = "ﱝ"

        if self.show_percentage:
            result = f"{icon} <span foreground='{colors['text']}'>{vol}%</span>"
        else:
            result = f"{icon}"

        return result

    def cmd_increase_vol(self) -> None:
        """Increase the volume and refresh volume and icon"""

        subprocess.call(["amixer -q sset Master 5%+"], shell=True)
        self.text = self.get_vol()
        self.bar.draw()

    def cmd_decrease_vol(self) -> None:
        """Decrease the volume and refresh volume and icon"""

        subprocess.call(["amixer -q sset Master 5%-"], shell=True)
        self.text = self.get_vol()
        self.bar.draw()

    def cmd_mute(self) -> None:
        """Toggle to mute/unmute volume and refresh icon"""

        subprocess.call(["amixer -q sset Master toggle"], shell=True)
        self.text = self.get_vol()
        self.bar.draw()

    def cmd_toggle_percentage(self) -> None:
        """Show or hide the percentage next to the icon"""
        if self.show_percentage:
            self.show_percentage = False
        else:
            self.show_percentage = True

        self.text = self.get_vol()
        self.bar.draw()
