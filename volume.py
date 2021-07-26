"""I don't want to poll alsa all the time but rather get the volume upon change"""

import subprocess
import re
from libqtile.widget import base
import fontawesome as fa

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
        self.vol = self.get_vol()
        self.text = self.get_icon(self.vol)

    def get_vol(self):
        """Get the volume value"""
        vol = subprocess.check_output(['amixer sget Master'], shell=True).decode('utf-8')

        if re.search('off', vol):
            vol = 0
        else:
            vol = self.vol_value.search(vol)
            vol = int(vol.groups()[0])

        return vol

    @classmethod
    def get_icon(cls, vol):
        """Match volume with appropriate icon"""

        if vol == 0:
            icon = fa.icons['volume-mute']
        elif vol >= 70:
            icon = fa.icons['volume-up']
        elif vol >= 40:
            icon = fa.icons['volume-down']
        elif vol < 40:
            icon = fa.icons['volume-off']

        return icon

    def cmd_increase_vol(self):
        """Increase the volume and refresh volume and icon"""

        subprocess.call(['amixer -q sset Master 5%+'], shell=True)
        self.vol = self.get_vol()
        self.text = self.get_icon(self.vol)
        self.bar.draw()

    def cmd_decrease_vol(self):
        """Decrease the volume and refresh volume and icon"""

        subprocess.call(['amixer -q sset Master 5%-'], shell=True)
        self.vol = self.get_vol()
        self.text = self.get_icon(self.vol)
        self.bar.draw()

    def cmd_mute(self):
        """Toggle to mute/unmute volume and refresh icon"""

        subprocess.call(['amixer -q sset Master toggle'], shell=True)
        self.vol = self.get_vol()
        self.text = self.get_icon(self.vol)
        self.bar.draw()
