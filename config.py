# -*- coding: utf-8 -*-
"""
 TO DO
- Set up the wifi widget for signal strength and icon
- Multi screen actions, maybe.
- Follow only URLs and nothing else. Smart setting not working the way I want.
- Spotify NowPlaying widget doesn't pick up songs playing in the event of Qtile restart. Low prio.
"""
import os
import re
import subprocess

from datetime import date
import fontawesome as fa
import iwlib
import netifaces as ni

from libqtile.config import Key, Screen, Group, Drag, Click, Match, EzKey, KeyChord
from libqtile.lazy import lazy
from libqtile import layout, bar, widget, hook, qtile
from libqtile.utils import send_notification

from battery import CustomBattery
from spotify import NowPlaying
from volume import VolumeCtrl
from colors import colors

home = os.path.expanduser('~')

MOD = 'mod4'

modifier_keys = {
        'M': 'mod4',
        'A': 'mod1',
        'C': 'control',
        'S': 'shift',
}

find_wifi_interface = re.compile('^wlp.')

NETWORK_INTERFACE = list(filter(find_wifi_interface.match, ni.interfaces()))[0]
TERMINAL = 'alacritty'
BROWSER = 'firefox'
CHAT = 'signal-desktop'
LAUNCHER = ''.join(['rofi -no-lazy-grab -show drun -modi drun -theme ', home, \
        '/.config/rofi/style_launcher'])
SWITCHER = ''.join(['rofi -show window -modi window -theme ', home, \
        '/.config/rofi/style_switcher'])
FILE_MANAGER = 'pcmanfm'
MUSIC_PLAYER = 'spotify'
MAIL = 'claws-mail'
MUSIC_CTRL = ('dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify '
            '/org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.')


group_assignments = {
    '1': ['Navigator'],
    '2': ['valheim.x86_64', 'battle.net.exe', 'wowclassic.exe', 'ck3', 'paradox launcher'],
    '3': ['claws-mail', 'discord', 'signal'],
    '4': ['spotify'],
    '5': ['Steam'],
}

steam_game = re.compile('^steam_app_.')
volume_level = re.compile(r'\[(\d?\d?\d?)%\]')

@hook.subscribe.startup_once
def autostart():
    """Autostart things from my script when qtile starts"""
    subprocess.call(''.join([home, '/.local/bin/startup']))

@hook.subscribe.float_change
def center_window():
    """Centers all the floating windows"""
    client = qtile.current_window
    if not client.floating:
        return

    screen_rect = qtile.current_screen.get_rect()

    center_x = screen_rect.x + screen_rect.width / 2
    center_y = screen_rect.y + screen_rect.height / 2

    x_pos = center_x - client.width / 2
    y_pos = center_y - client.height / 2

    # don't go off the right...
    x_pos = min(x_pos, screen_rect.x + screen_rect.width - client.width)
    # or left...
    x_pos = max(x_pos, screen_rect.x)
    # or bottom...
    y_pos = min(y_pos, screen_rect.y + screen_rect.height - client.height)
    # or top
    y_pos = max(y_pos, screen_rect.y)

    client.x = int(round(x_pos))
    client.y = int(round(y_pos))
    qtile.current_group.layout_all()

@hook.subscribe.client_new
def assign_app_group(client):
    """Decides which apps go where when they are launched"""

    try:
        wm_class = client.window.get_wm_class()[0]

        if steam_game.search(wm_class): # I want all steam games on workspace 2
            client.togroup('2')
        else:
            group = list(k for k, v in group_assignments.items() if wm_class in v)[0]
            client.togroup(group)

    except IndexError:
        return

@hook.subscribe.client_name_updated
def spotify_handle(client):
    """Push Spotify to correct group since it's wm_class setting is slow"""

    try:
        if client.window.get_wm_class()[0] == "spotify":
            client.togroup('4')
        else:
            return

    except IndexError:
        return

def check_if_running(app):
    """Check if the app being launched is already running, if so do nothing"""
    def run_cmd(qtile_cmd):
        """Run the subprocess check and raise app if it's running"""
        if qtile_cmd:
            try:

                # First a "temporary" fix to catch Signal and Steam
                if app == 'signal-desktop':
                    app_wmclass = 'signal'
                elif app == 'steam-native':
                    app_wmclass = 'steam'
                else:
                    app_wmclass = app

                subprocess.check_output([''.join(['pgrep -f ', app_wmclass])], shell=True)

                subprocess.run([''.join(['wmctrl -x -a ', app_wmclass])], check=True, shell=True)
            except subprocess.CalledProcessError:
                qtile.cmd_spawn(app)
        else:
            return
    return run_cmd

def notification(request):
    """Used for mouse callbacks from widgets to send notifications"""
    if request == 'wifi':
        try:
            interface = iwlib.get_iwconfig(NETWORK_INTERFACE)
            quality = interface['stats']['quality']
            quality = interface['stats']['quality']
            quality = round((quality / 70)*100)
            ssid = interface['ESSID']
            title = "Wifi"
            message = "".join(
                [str(ssid, encoding = 'utf-8'), "\nSignal strength: {}%".format(quality)])

        except KeyError:
            title = "Disconnected"
            message = ""

    elif request == 'date':
        todaysdate = date.today()
        weekday = todaysdate.strftime("%A")
        title =  "".join([str(todaysdate), " (", str(weekday),")"])
        message = "".join(["Week ", str(date.today().isocalendar()[1])])

    elif request == 'battery':
        title = "Battery status"
        message = str(subprocess.check_output(
            ["acpi"],
            shell=True), encoding = 'utf-8')

    elif request == 'volume':
        vol = subprocess.check_output(['amixer sget Master'], shell = True).decode('utf-8')

        if re.search('off', vol):
            vol = 0
        else:
            vol = volume_level.search(vol)
            vol = int(vol.groups()[0])

        title = "Volume level"
        message = "{}%".format(vol)

    return send_notification(title, message, timeout = 2000, urgent = False)

# Keybinds
keys = [
        # Switch focus between windows
        EzKey('M-<Down>', lazy.layout.down()),
        EzKey('M-<Up>', lazy.layout.up()),
        EzKey('M-<Left>', lazy.layout.left()),
        EzKey('M-<Right>', lazy.layout.right()),

        # Move windows between left/right columns or move up/down in current stack
        EzKey('M-S-<Left>', lazy.layout.swap_left()),
        EzKey('M-S-<Right>', lazy.layout.swap_right()),
        EzKey('M-S-<Down>', lazy.layout.shuffle_down()),
        EzKey('M-S-<Up>', lazy.layout.shuffle_up()),

        # Grow/shrink windows
        EzKey('M-C-<Left>', lazy.layout.shrink_main()),
        EzKey('M-C-<Right>', lazy.layout.grow_main()),
        EzKey('M-C-<Down>', lazy.layout.shrink()),
        EzKey('M-C-<Up>', lazy.layout.grow()),

        # Various window controls
        EzKey('M-n', lazy.layout.reset()),
        EzKey('M-f', lazy.window.toggle_fullscreen()),
        EzKey('M-q', lazy.window.kill()),
        EzKey('M-S-f', lazy.window.toggle_floating()),
        EzKey('M-<space>', lazy.next_layout()),
        EzKey('M-S-<space>', lazy.layout.flip()),
        EzKey('M-<Tab>', lazy.spawn(SWITCHER)),
        EzKey('M-S-<Tab>', lazy.window.bring_to_front()),
        EzKey('M-S-b', lazy.hide_show_bar()),

        # Some app shortcuts
        EzKey('M-b', lazy.function(check_if_running(BROWSER))),
        EzKey('M-<Return>', lazy.spawn(TERMINAL)),
        EzKey('M-S-<Return>', lazy.spawn(FILE_MANAGER)),
        EzKey('M-r', lazy.spawn(LAUNCHER)),
        EzKey('M-d', lazy.function(check_if_running('discord'))),
        EzKey('M-s', lazy.function(check_if_running(MUSIC_PLAYER))),
        EzKey('M-g', lazy.function(check_if_running('steam-native'))),
        EzKey('M-c', lazy.function(check_if_running(CHAT))),
        EzKey('M-m', lazy.function(check_if_running(MAIL))),
        EzKey('M-p', lazy.spawn('passmenu')),

        # KeyChords for some special actions
        KeyChord([MOD], 'k', [
            EzKey('c', lazy.spawn('rofi-confedit')),
            EzKey('q', lazy.spawn('alacritty -e vim .config/qtile/')),
            EzKey('u', lazy.spawn('alacritty -e yay -Syu')),
            EzKey('l', lazy.spawn('alacritty -e bat .local/share/qtile/qtile.log')),
        ]),

        # Spotify controls, lacking real media keys :(
        EzKey('M-8', lazy.spawn(''.join([MUSIC_CTRL, 'PlayPause']))),
        EzKey('M-9', lazy.spawn(''.join([MUSIC_CTRL, 'Next']))),
        EzKey('M-7', lazy.spawn(''.join([MUSIC_CTRL, 'Previous']))),

        # Media volume keys, if available
        EzKey('<XF86AudioMute>', lazy.widget['volumectrl'].mute()),
        EzKey('<XF86AudioLowerVolume>', lazy.widget['volumectrl'].decrease_vol()),
        EzKey('<XF86AudioRaiseVolume>', lazy.widget['volumectrl'].increase_vol()),

        # System controls
        EzKey('M-l', lazy.spawn(''.join([home, '.local/bin/lock']))),
        EzKey('M-C-r', lazy.restart()),
        EzKey('M-C-q', lazy.shutdown()),
        EzKey('M-C-<Escape>', lazy.spawn('poweroff')),

    ]
# Groups
group_settings = [
        ('1', {'label': fa.icons['circle'], 'layout': 'monadtall'}),
        ('2', {'label': fa.icons['circle'], 'layout': 'monadtall'}),
        ('3', {'label': fa.icons['circle'], 'layout': 'monadtall'}),
        ('4', {'label': fa.icons['circle'], 'layout': 'monadtall'}),
        ('5', {'label': fa.icons['circle'], 'layout': 'monadtall'}),
        ('6', {'label': fa.icons['circle'], 'layout': 'monadtall'}),
    ]

groups = [Group(name, **kwargs) for name, kwargs in group_settings]

for i in groups:
    keys.extend([
    Key([MOD], i.name, lazy.group[i.name].toscreen()),
    Key([MOD, 'shift'], i.name, lazy.window.togroup(i.name)),
    ])

# Layouts
layout_theme = {
        'border_width': 2,
        'border_focus': colors['main'],
        'border_normal': colors['separator'],
        }

layouts = [
        layout.MonadTall(
        **layout_theme,
        single_border_width = 0
        ),
        layout.MonadWide(
        **layout_theme,
        single_border_width = 0
        )
        ]

floating_layout = layout.Floating(float_rules=[
      *layout.Floating.default_float_rules,
      Match(wm_class='Nm-connection-editor'),
      Match(wm_class='pinentry-gtk-2'),
      Match(wm_class='Lxappearance'),
      Match(wm_class='Xfce4-taskmanager'),
      Match(wm_class='VirtualBox Manager'),
      Match(wm_class='pavucontrol'),
      Match(title='Confirm File Replacing') # This is to float the copy/replace dialog of Pcmanfm
    ],
    **layout_theme)

# Mouse
mouse = [
        Drag([MOD], 'Button1', lazy.window.set_position_floating(),
            start=lazy.window.get_position()),
        Drag([MOD], 'Button3', lazy.window.set_size_floating(),
            start=lazy.window.get_size()),
        Click([MOD], 'Button2', lazy.window.toggle_floating())
        ]

# Widgets & extension defaults
widget_defaults = dict(
        font = 'Source Sans Pro Semibold',
        fontsize = 15,
        background = colors['background'],
        foreground = colors['text']
        )

extension_defaults = widget_defaults.copy()

# Widgets
widgets = [
#            widget.CurrentLayoutIcon(
#                custom_icon_paths = [''.join([home, '/.config/qtile/icons/'])],
#                foreground = colors['text'],
#                background = colors['main'],
#                padding = 3,
#                scale = 0.5
#                ),
            widget.Sep(
                padding = 8,
                foreground = colors['background'],
                ),
            widget.GroupBox(
                margin_x = 0,
                fontsize = 14,
                hide_unused = False,
                disable_drag = True,
                padding = 8,
                borderwidth = 0,
                active = colors['text'],
                inactive = colors['secondary'],
                rounded = False,
                highlight_color = colors['background'],
                highlight_method = 'text',
                this_current_screen_border = colors['main'],
                this_screen_border = colors['main'],
                foreground = colors['text'],
                urgent_alert_method = 'text',
                urgent_text = colors['urgent']
                ),
            widget.Sep(
                padding = 22,
                size_percent = 100,
                linewidth = 2,
                foreground = colors['separator']
                ),
            widget.Sep(
                padding = 8,
                foreground = colors['background']
                ),
            widget.TextBox(
                text = fa.icons['arrow-circle-right'],
                foreground = colors['main'],
                padding = 0
                ),
            widget.WindowName(
                max_chars = 50,
                empty_group_string = "Desktop",
                ),
            widget.Spacer(
                length = bar.STRETCH,
                ),
            NowPlaying(
                mouse_callbacks = {'Button1': lambda: qtile.cmd_spawn(''.join([MUSIC_CTRL, \
                                                'PlayPause'])),
                                   'Button3': lambda: qtile.cmd_simulate_keypress([MOD], "s")}
                ),
            widget.Sep(
                padding = 8,
                foreground = colors['background']
                ),
            widget.TextBox(
                text = "  " + fa.icons['circle'],
                padding= -14,
                fontsize = 37,
                foreground = colors['main']
                ),
            widget.Systray(
                padding = 14,
                background = colors['main']
                ),
            widget.Sep(
                foreground = colors['main'],
                background = colors['main'],
                padding = 16
                ),
            VolumeCtrl(
                background = colors['main'],
                padding = 0,
                mouse_callbacks={'Button3': lambda: lazy.function(notification('volume'))},
                ),
            widget.Sep(
                foreground = colors['main'],
                background = colors['main'],
                padding = 16
                ),
            widget.Wlan(
                format = fa.icons['wifi'],
                interface = NETWORK_INTERFACE,
                disconnected_message = fa.icons['times'],
                background = colors['main'],
                update_interval = 7,
                padding = 0,
                mouse_callbacks={'Button3': lambda: qtile.cmd_spawn(''.join([TERMINAL, \
                                            ' -e nmtui'])),
                                 'Button1': lambda: lazy.function(notification('wifi'))}
                ),
            widget.Sep(
                foreground = colors['main'],
                background = colors['main'],
                padding = 16
                ),
            widget.Clock(
                foreground = colors['text'],
                background = colors['main'],
                format = '%H:%M',
                padding = 0,
                mouse_callbacks = {'Button1': lambda: lazy.function(notification('date'))}
                ),
            widget.Sep(
                padding = 10,
                foreground = colors['main'],
                background = colors['main']
                )
        ]

# Check if the computer is a laptop basically, and if it is add battery widget
if os.path.isfile('/usr/bin/acpi'):
    widgets.insert(-2, CustomBattery(
        padding = 0,
        background = colors['main'],
        low_foreground = colors['urgent'],
        mouse_callbacks = {'Button1': lambda: lazy.function(notification('battery'))}
        ))
    widgets.insert(-2, widget.Sep(
        foreground = colors['main'],
        background = colors['main'],
        padding = 14
        ))

# Bar
bar = bar.Bar(widgets=widgets, size = 32)

# Screens
screens = [Screen(top=bar)]

dgroups_key_binder = None
dgroups_app_rules = []
follow_mouse_focus = True
bring_front_click = True
cursor_warp = False
reconfigure_screens = True
auto_fullscreen = True
auto_minimize = True
focus_on_window_activation = 'smart'
wmname = "LG3D"
