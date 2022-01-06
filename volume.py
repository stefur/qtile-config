"""I don't want to poll alsa all the time but rather get the volume upon change"""

import subprocess
import re
from libqtile.widget import base

class VolumeCtrl(base._TextBox):
    """Use amixer to get the volume, transform it to a readable format and return an icon"""

    def __init__(self, **config):
        base._TextBox.__init__(self, **config)

        self.add_callbacks({
            'Button1': self.cmd_mute,
            'Button4': self.cmd_increase_vol,
            'Button5': self.cmd_decrease_vol,
        })

        self.vol_value = re.compile(r'\[(\d?\d?\d?)%\]')
        self.text = self.get_vol()

    def get_vol(self):
        """Get the volume value"""
        vol = subprocess.check_output(['amixer sget Master'], shell=True).decode('utf-8')

        if re.search('off', vol):
            vol = "Muted"
        else:
            vol = self.vol_value.search(vol).groups()[0]
            vol = f"{vol}%"

        return vol

    def cmd_increase_vol(self):
        """Increase the volume and refresh volume and icon"""

        subprocess.call(['amixer -q sset Master 5%+'], shell=True)
        self.text = self.get_vol()
        self.bar.draw()

    def cmd_decrease_vol(self):
        """Decrease the volume and refresh volume and icon"""

        subprocess.call(['amixer -q sset Master 5%-'], shell=True)
        self.text = self.get_vol()
        self.bar.draw()

    def cmd_mute(self):
        """Toggle to mute/unmute volume and refresh icon"""

        subprocess.call(['amixer -q sset Master toggle'], shell=True)
        self.text = self.get_vol()
        self.bar.draw()
