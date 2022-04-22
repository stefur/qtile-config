"""I don't want to poll alsa all the time but rather get the volume upon change"""
from __future__ import annotations

import subprocess
import re
from libqtile import widget

from colors import colors

volume_level_icons: dict[str, int] = {"墳": 66, "奔": 33, "奄": 0}


class VolumeCtrl(widget.TextBox):
    """Use amixer to get the volume, transform it to a readable format and return an icon"""

    def __init__(self, **config):
        widget.TextBox.__init__(self, **config)

        self.add_callbacks(
            {
                "Button1": self.cmd_mute,
                "Button3": self.cmd_toggle_text,
                "Button4": self.cmd_increase_vol,
                "Button5": self.cmd_decrease_vol,
            }
        )

        self.show_text: bool = False
        self.vol_value = re.compile(r"\[(\d?\d?\d?)%\]")
        self.text = self.get_vol()

    def get_vol(self) -> str:
        """Get the volume value"""
        output = subprocess.check_output(["amixer sget Master"], shell=True).decode(
            "utf-8"
        )

        vol = int(self.vol_value.search(output).groups()[0])  # type: ignore
        icon = next(iter({k: v for k, v in volume_level_icons.items() if vol >= v}))

        if re.search("off", output):
            vol = 0
            icon = "婢"

        if self.show_text:
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

    def cmd_toggle_text(self) -> None:
        """Show or hide the percentage next to the icon"""
        if self.show_text:
            self.show_text = False
        else:
            self.show_text = True

        self.text = self.get_vol()
        self.bar.draw()
