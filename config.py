# -*- coding: utf-8 -*-
# stefur config

"""
 TO DO
- Rewrite color and appss to dict (maybe)
- Figure out why custom layout icon path is not working (using the default path atm)
- Set up the wifi widget for signal strength and icon,
- Define more stuff such as wifi interface for easier configuration
"""

from libqtile.config import Key, Screen, Group, Drag, Click, Match
from libqtile.lazy import lazy
from libqtile import layout, bar, widget, hook, qtile
from typing import List  # noqa: F401

import os
import re
import subprocess

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from libqtile.widget import base

import iwlib

from datetime import date

# My home

home = os.path.expanduser('~/')

# Mod key = Super key

mod = "mod4"

# Applications for launch shortcuts etc

terminal = "termite"
browser = "firefox"
chat = "signal-desktop -- %u"
passwords = "keepassxc"
launcher = "rofi -no-lazy-grab -show drun -modi drun -theme " + home + ".config/rofi/style_launcher"
switcher = "rofi -show window -modi window -theme " + home + ".config/rofi/style_switcher"
file_manager = "pcmanfm"
music_player = "spotify"
mail = "thunderbird"

# Colors and fonts

col_main        = "#339966"   # Main color, for borders on active window and workspaces, currently green
col_secondary   = "#626a66"   # Secondary color, for inactive window borders, currently dark green
col_background  = "#222222"   # All backgrounds, for example bars and widgets, currently dark gray
col_text        = "#ffffff"   # All text, for readability currently white
col_selected    = "#434758"   # Selected workspace background, blueish shade of dark gray
col_urgent      = "#993932"   # All urgent borders and text, currently pale red

text_font       = "Source Sans Pro SemiBold" # Used for widgets mainly
icon_font       = "Font Awesome 5 Free Solid" # Used for workspace icons

# Hook to start my stuff

@hook.subscribe.startup_once
def autostart():
    subprocess.call(home + ".config/startup.sh")

# Workspace assigned to wm_classes

workspace = {
    "1":  ["Navigator", "Firefox",
           "navigator", "firefox", ],
    "2": ["steam_app_", "valheim.x86_64", "battle.net.exe"],
    "3": ["Signal", "Thunderbird", "Discord",
          "signal", "Mail", "discord"],
    "4": ["Spotify", "spotify"],
    "5": ["Steam", "steam"],
}

# Hook to launch app in assigned workspace

@hook.subscribe.client_new
def assign_app_group(client):
    wm_class = client.window.get_wm_class()[0]
    steam_app = re.search("^steam_app_.", wm_class) # Special handling of steam games, I want all of them on workspace 2
    if steam_app:
        client.togroup("2")
    else:
        for i in range(len(workspace)):
            if wm_class in list(workspace.values())[i]:
                group = list(workspace.keys())[i]
                client.togroup(group)

# Function to only run apps that are not already running

def check_if_running(app):
    def cmd(qtile):
       try:
           subprocess.check_output(['pgrep ' + app], shell=True)
       except:
            qtile.cmd_spawn(app)
    return cmd

# Some Spotify controls to add PlayPause / Next / Previous

music_ctrl = ("dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify "
             "/org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.")

# A custom widget to show what Spotify is playing, based on mpris2

class SpotifyPlaying(base._TextBox):
    def __init__(self, **config):
        base._TextBox.__init__(self, **config)
        dbus_loop = DBusGMainLoop()
        bus = dbus.SessionBus(mainloop=dbus_loop)
        bus.add_signal_receiver(self.update, 'PropertiesChanged',
            'org.freedesktop.DBus.Properties', 'org.mpris.MediaPlayer2.spotify',
            '/org/mpris/MediaPlayer2')

        bus.add_signal_receiver(self.clear, 'NameOwnerChanged', 'org.freedesktop.DBus',
            None, '/org/freedesktop/DBus', arg0="org.mpris.MediaPlayer2.spotify")

    def clear(self, name, old_owner, new_owner):
        if name == "org.mpris.MediaPlayer2.spotify":
            if old_owner:
                self.text = ''
                self.bar.draw()

    def update(self, interface_name, changed_properties, invalidated_properties):
        self.displaytext = 'testtext'
        self.display_metadata = ['xesam:artist', 'xesam:title']
        self.statussymbol = ''
        metadata = None
        playbackstatus = None
        metadata = changed_properties.get('Metadata')
        playbackstatus = changed_properties.get('PlaybackStatus')

        if metadata:
            self.displaytext = ' - '.join([metadata.get(x)
                if isinstance(metadata.get(x), dbus.String)
                else ' + '.join([y for y in metadata.get(x)
                if isinstance(y, dbus.String)])
                for x in self.display_metadata if metadata.get(x)])
            self.displaytext.replace('\n', '')
            if len(self.displaytext) > 35:
                self.displaytext = self.displaytext[:35]
                self.displaytext += ' ...'
                if ('(' in self.displaytext) and (')' not in self.displaytext):
                    self.displaytext += ')'

        if playbackstatus:
            if playbackstatus == 'Paused':
                self.statussymbol = '<span foreground="' + col_main + '"></span>  '
            elif playbackstatus == 'Playing':
                self.statussymbol = '<span foreground="' + col_main + '"></span>  '

        self.text = self.statussymbol + self.displaytext
        self.bar.draw()

# Function to get todays date and current week, then send it as a notification. Used for mouse callback on clock widget

def notify_date():
    notify_interface = dbus.Interface(
        object=dbus.SessionBus().get_object("org.freedesktop.Notifications",
                                            "/org/freedesktop/Notifications"),
        dbus_interface="org.freedesktop.Notifications")

    notification  = notify_interface.Notify("Date", 0, "",
    str(date.today()),"Week " + str(date.today().isocalendar()[1]), [], {"urgency": 1}, 10000)

    return notification

# Function to get the wifi signal strength, then send it as a notification. Used for mouse callback on wifi widget. Temp solution until I cba to make a custom widget

def notify_wifi():

    try:
        interface = iwlib.get_iwconfig('wlp7s0')
        quality = interface['stats']['quality']
        signal = round((quality / 70)*100)

    except:
        signal = "Disconnected"

    notify_interface = dbus.Interface(object=dbus.SessionBus().get_object("org.freedesktop.Notifications",
                                        "/org/freedesktop/Notifications"), dbus_interface="org.freedesktop.Notifications")

    notification = notify_interface.Notify("Wifi signal", 0, "",
     "{}%".format(signal), "", [], {"urgency": 1}, 10000)

# Custom volume function, since I don't want to poll alsa all the time but rather get the volume upon change

class Vol(base._TextBox):

    def __init__(self, **config):
        base._TextBox.__init__(self, **config)

        self.add_callbacks({
            'Button1': self.cmd_mute,
            'Button4': self.cmd_increase_vol,
            'Button5': self.cmd_decrease_vol,
        })

        vol = self.get_volume()

        if vol == 0:
            self.text = ""
        elif  vol <= 30:
            self.text = ""
        elif vol > 80:
            self.text = ""
        elif vol > 30:
            self.text = ""

    def get_volume(self):
        try:
            vol = subprocess.check_output(["amixer sget Master"], shell=True).decode('utf-8')

            if re.search("off", vol):
                vol = 0

            else:
                vol = re.compile(r'\[(\d?\d?\d?)%\]').search(vol)
                vol = int(vol.groups()[0])

        except:
            vol = "Is alsamixer installed?"

        return vol

    def icon(self):
        vol = self.get_volume()

        if vol == 0:
            self.text = ""
        elif vol <= 30:
            self.text = ""
        elif vol > 70:
            self.text = ""
        elif vol > 30:
            self.text = ""

        self.bar.draw()
        return self.text

    def cmd_increase_vol(self):
            subprocess.call(['amixer -q sset Master 2%+'], shell=True)
            vol = self.get_volume()
            self.text = '{}%'.format(vol)
            self.bar.draw()
            self.timeout_add(3, self.icon)

    def cmd_decrease_vol(self):
            subprocess.call(['amixer -q sset Master 2%-'], shell=True)
            vol = self.get_volume()
            self.text = '{}%'.format(vol)
            self.bar.draw()
            self.timeout_add(3, self.icon)

    def cmd_mute(self):
            subprocess.call(['amixer -q sset Master toggle'], shell=True)
            vol = self.get_volume()
            self.text = self.icon()
            self.bar.draw()

# Hook to fallback to the first group with windows available when the last window of a group is killed

@hook.subscribe.client_killed
def fallback(window):
    if window.group.windows != {window}:
        return

    for group in qtile.groups:
        if group.windows:
            qtile.current_screen.toggle_group(group)
            return
    qtile.current_screen.toggle_group(qtile.groups[0])

# Keybinds

keys = [

# Switch between windows

    Key([mod], "Left", lazy.layout.left(), desc="Move focus to left"),
    Key([mod], "Right", lazy.layout.right(), desc="Move focus to right"),
    Key([mod], "Down", lazy.layout.down(), desc="Move focus down"),
    Key([mod], "Up", lazy.layout.up(), desc="Move focus up"),


# Move windows between left/right columns or move up/down in current stack

    Key([mod, "shift"], "Left", lazy.layout.shuffle_left()),
    Key([mod, "shift"], "Right", lazy.layout.shuffle_right()),
    Key([mod, "shift"], "Down", lazy.layout.shuffle_down()),
    Key([mod, "shift"], "Up", lazy.layout.shuffle_up()),

# Grow/shrink windows

    Key([mod, "control"], "Left", lazy.layout.shrink(),
                                  lazy.layout.grow_left(),
                                  lazy.layout.increase_nmaster()),
    Key([mod, "control"], "Right", lazy.layout.grow(),
                                   lazy.layout.grow_right(),
                                   lazy.layout.decrease_nmaster()),
    Key([mod, "control"], "Down", lazy.layout.grow_down()),
    Key([mod, "control"], "Up", lazy.layout.grow_up()),

# Various window controls

    Key([mod], "n", lazy.layout.normalize()),
    Key([mod], "f", lazy.window.toggle_fullscreen()),
    Key([mod], "q", lazy.window.kill()),
    Key([mod, "shift"], "f", lazy.window.toggle_floating()),
    Key([mod], "space", lazy.next_layout()),
    Key([mod], "Tab", lazy.spawn(switcher)),
    Key([], "Print", lazy.spawn("scrot")),

# Some app shortcuts

    Key([mod], "b", lazy.function(check_if_running(browser)), lazy.group["1"].toscreen(toggle=False)),
    Key([mod], "Return", lazy.spawn(terminal)),
    Key([mod, "shift"], "Return", lazy.spawn(file_manager)),
    Key([mod], "d", lazy.spawn(launcher)),
    Key([mod], "m", lazy.function(check_if_running(music_player)), lazy.group["4"].toscreen(toggle=False)),
    Key([mod], "g", lazy.spawn("steam-native"), lazy.group["5"].toscreen(toggle=False)),
    Key([mod], "c", lazy.function(check_if_running(chat)), lazy.group["3"].toscreen(toggle=False)),
    Key([mod], "k", lazy.spawn(passwords)),
    Key([mod], "t", lazy.spawn(mail), lazy.group["3"].toscreen(toggle=False)),

# Spotify controls, lacking real media keys

    Key(["control"], "8", lazy.spawn(music_ctrl + "PlayPause")),
    Key(["control"], "9", lazy.spawn(music_ctrl + "Next")),
    Key(["control"], "7", lazy.spawn(music_ctrl + "Previous")),

# System controls

    Key([mod, "control"], "r", lazy.restart()),
    Key([mod, "control"], "q", lazy.shutdown()),
    Key([mod, "control"], "Escape", lazy.spawn("poweroff")),
]

# Names, labels and layout for each group

groups = []
group_names = ["1", "2", "3", "4", "5", "6", "7", "8"]
group_labels = ["", "", "", "", "", "", "", ""]
group_layouts = ["monadtall", "max", "columns", "monadtall", "monadtall", "monadtall", "monadtall", "monadtall"]

for i in range(len(group_names)):
    groups.append(
        Group(name=group_names[i], label=group_labels[i], layout=group_layouts[i])
    )

for i in groups:
    keys.extend([
        Key([mod], i.name, lazy.group[i.name].toscreen()),
        Key([mod, "shift"], i.name, lazy.window.togroup(i.name)),
    ])

# Default settings for all layouts

layout_theme = {"border_width": 1,
                "border_focus": col_main,
                "border_normal": col_secondary,
                }

# Layouts I use

layouts = [
    layout.MonadTall(
                    **layout_theme,
                    ratio = 0.65,
                    single_border_width = 0
    ),
    layout.Columns(**layout_theme),
    layout.Max(**layout_theme),
]

# Widgets

widget_defaults = dict(
    font = text_font,
    fontsize = 14,
    background = col_background,
    foreground = col_text
)

extension_defaults = widget_defaults.copy()

def init_widgets_list():
    widgets_list = [
            widget.CurrentLayoutIcon(
                custom_icon_paths = ["$HOME/.config/qtile/icons/"],
                foreground = col_text,
                background = col_main,
                padding = 3,
                scale = 0.5
                ),
            widget.GroupBox(
                font = icon_font,
                margin_y = 3,
                margin_x = 0,
                hide_unused = True,
                disable_drag = True,
                padding_y = 5,
                padding_x = 8,
                borderwidth = 2,
                active = col_text,
                inactive = col_text,
                rounded = False,
                highlight_color = col_selected,
                highlight_method = "line",
                this_current_screen_border = col_main,
                this_screen_border = col_secondary,
                foreground = col_text,
                urgent_alert_method = "line",
                urgent_border = col_urgent
                ),
            widget.Spacer(
                length = bar.STRETCH,
                ),
            SpotifyPlaying(
                mouse_callbacks = {'Button1': lambda: qtile.cmd_spawn(music_ctrl + "PlayPause")}
               ),
            widget.Sep(
                padding = 4,
                foreground = col_background
                ),
              widget.TextBox(
                text='',
                padding = 0,
                fontsize = 72,
                foreground = col_main
                ),
            Vol(
                background = col_main,
                padding = 0
                ),
            widget.Sep(
                foreground = col_main,
                background = col_main,
                padding = 2
                ),
            widget.Systray(
                padding = 12,
                icon_size = 17,
                background = col_main,
                ),
            widget.Sep(
                foreground = col_main,
                background = col_main,
                padding = 12
                ),
            widget.Wlan(
                format = ' ',
                interface = 'wlp7s0',
                disconnected_message = '',
                background = col_main,
                update_interval = 7,
                padding = 0,
                mouse_callbacks={"Button1": lambda: qtile.cmd_spawn(terminal + " -e nmtui"),
                                 "Button3": lambda: lazy.function(notify_wifi())}
                ),
            widget.Sep(
                foreground = col_main,
                background = col_main,
                padding = 10
                ),
            widget.Clock(
                foreground = col_text,
                background = col_main,
                format = "%H:%M",
                padding = 0,
                mouse_callbacks = {'Button1': lambda: lazy.function(notify_date())}
                ),
            widget.Sep(
                padding = 10,
                foreground = col_main,
                background = col_main
                )
    ]

    return widgets_list

# The bar

screens = [Screen(top=bar.Bar(widgets=init_widgets_list(), opacity=1.0, size=25))]

mouse = [
    Drag([mod], "Button1", lazy.window.set_position_floating(),
         start=lazy.window.get_position()),
    Drag([mod], "Button3", lazy.window.set_size_floating(),
         start=lazy.window.get_size()),
    Click([mod], "Button2", lazy.window.toggle_floating())
]

# Floating things

floating_layout = layout.Floating(float_rules=[
    *layout.Floating.default_float_rules,
    Match(wm_class='Nm-connection-editor'),
    Match(wm_class='Lxappearance'),
    Match(wm_class='Xfce4-taskmanager'),
    Match(title='Confirm File Replacing') # This is to float only copy/replace window of Pcmanfm
],
**layout_theme)

dgroups_key_binder = None
dgroups_app_rules = []
follow_mouse_focus = True
bring_front_click = True
cursor_warp = False
auto_fullscreen = True
focus_on_window_activation = "smart"
main = None

# Switch wmname in case it is necessary. LG3D that happens to be on java's whitelist.
# wmname = "LG3D"
wmname = "Qtile"
