"""I don't want to poll alsa all the time but rather get the volume upon change"""
from __future__ import annotations

import subprocess
import re
from libqtile import widget
from libqtile.log_utils import logger

from colors import colors

volume_level_icons: dict[str, int] = {"\ufa7d": 66, "\ufa7f": 33, "\ufa7e": 0}


class VolumeCtrl(widget.TextBox):
    """Use amixer to get the volume, transform it to a readable format and return an icon"""

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
        self.vol_value = re.compile(r"\[(\d?\d?\d?)%\]")
        self.get_vol()

    def get_vol(self) -> None:
        """Get the volume value"""

        try:
            output = subprocess.check_output(["amixer sget Master"], shell=True).decode(
                "utf-8"
            )
            vol = int(self.vol_value.search(output).groups()[0])  # type: ignore
            icon = next(iter({k: v for k, v in volume_level_icons.items() if vol >= v}))

            if re.search("off", output):
                vol = 0
                icon = "\ufa80"

            if self.show_text:
                self.text = f"{icon} <span foreground='{colors['text']}'>{vol}%</span>"
            else:
                self.text = f"{icon}"

            self.bar.draw()

        except Exception as err:
            logger.debug(f"Failed to get amixer volume level: {err}")

    def increase_vol(self) -> None:
        """Increase the volume and refresh volume and icon"""

        subprocess.call(["amixer -q sset Master 5%+"], shell=True)
        self.get_vol()

    def decrease_vol(self) -> None:
        """Decrease the volume and refresh volume and icon"""

        subprocess.call(["amixer -q sset Master 5%-"], shell=True)
        self.get_vol()

    def mute(self) -> None:
        """Toggle to mute/unmute volume and refresh icon"""

        subprocess.call(["amixer -q sset Master toggle"], shell=True)
        self.get_vol()

    def toggle_text(self) -> None:
        """Show or hide the percentage next to the icon"""
        if self.show_text:
            self.show_text = False
        else:
            self.show_text = True

        self.get_vol()
