# -*- coding: utf-8 -*-
"""My qtile config"""

import os
import re
import subprocess

from datetime import date
import fontawesome as fa
import iwlib
import netifaces as ni

from libqtile.config import Key, Screen, Group, Drag, Click, \
                            Match, EzKey, KeyChord, ScratchPad, DropDown
from libqtile.lazy import lazy
from libqtile import layout, bar, widget, hook, qtile
from libqtile.utils import send_notification

from battery import CustomBattery
from spotify import NowPlaying
from volume import VolumeCtrl
from colors import colors

MOD = 'mod4'

modifier_keys = {
        'M': 'mod4',
        'A': 'mod1',
        'C': 'control',
        'S': 'shift',
}

wifi_interface = re.compile('^wlp.|^wlan.')
steam_game = re.compile('^steam_app_.')
volume_level = re.compile(r'\[(\d?\d?\d?)%\]')

NETWORK_INTERFACE = list(filter(wifi_interface.match, ni.interfaces()))[0]
TERMINAL = 'alacritty'
BROWSER = 'firefox'
LAUNCHER = 'rofi -no-lazy-grab -show drun -modi drun -theme ~/.config/rofi/style_launcher'
SWITCHER = 'rofi -show window -modi window -theme ~/.config/rofi/style_switcher'
FILE_MANAGER = 'pcmanfm'
MUSIC_CTRL = ('dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify '
            '/org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.')

group_assignments = {
    '1': ['Navigator'],
    '2': ['valheim.x86_64', 'battle.net.exe', 'wowclassic.exe', 'ck3', 'paradox launcher'],
    '3': ['claws-mail', 'discord', 'signal'],
    '4': ['spotify'],
    '5': ['Steam'],
}

@hook.subscribe.startup_once
def autostart():
    """Autostart things from script when qtile starts"""
    with subprocess.Popen("startup", shell = True) as process:
        hook.subscribe.shutdown(process.terminate)

@hook.subscribe.client_urgent_hint_changed
def follow_links(client):
    """If Firefox changes urgency hint go to it, focus_on_window_activation must be set to urgent"""
    if client.window.get_wm_class()[0] == "Navigator":
        subprocess.run([''.join(['wmctrl -x -a ', BROWSER])], check = True, shell = True)
    else:
        return

@hook.subscribe.float_change
def center_window():
    """Centers all the floating windows"""
    client = qtile.current_window

    if not client.floating or client.fullscreen: # Don't center if not floating or fullscreen
        return

    screen_rect = qtile.current_screen.get_rect()

    center_x = screen_rect.x + screen_rect.width / 2
    center_y = screen_rect.y + screen_rect.height / 2

    x_pos = center_x - client.width / 2
    y_pos = center_y - client.height / 2

    x_pos = min(x_pos, screen_rect.x + screen_rect.width - client.width)
    x_pos = max(x_pos, screen_rect.x)
    y_pos = min(y_pos, screen_rect.y + screen_rect.height - client.height)
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
def push_spotify(client):
    """Push Spotify to correct group since it's wm_class setting is slow"""

    try:
        if client.window.get_wm_class()[0] == "spotify":
            client.togroup('4')
        else:
            return

    except IndexError:
        return

@hook.subscribe.client_killed
def fallback_default_layout(*args):
    """Reset a workspace to default layout when theres is only one window left"""
    try:
        win_count = len(qtile.current_group.windows)

    except AttributeError:
        win_count = 0

    if win_count > 2:
        return

    qtile.cmd_to_layout_index(0)

def run_or_raise(app):
    """Check if the app being launched is already running, if so do nothing"""
    def run_cmd(qtile):
        """Run the subprocess check and raise app if it's running"""
        if qtile:
            try:
                # First a "temporary" fix to catch Signal and Steam
                if app == 'signal-desktop':
                    app_wmclass = 'signal'
                elif app == 'steam-native':
                    app_wmclass = 'steam'
                else:
                    app_wmclass = app

                subprocess.check_output([''.join(['pgrep -f ', app_wmclass])], shell = True)

                subprocess.run([''.join(['wmctrl -x -a ', app_wmclass])], check = True, shell = True)

            except subprocess.CalledProcessError:
                qtile.cmd_spawn(app)
        else:
            return
    return run_cmd

def notification(request):
    """Used for mouse callbacks from widgets to send notifications"""
    def _notification(qtile):
        """Also used for key combination shortcuts"""
        if request == 'wifi':
            try:
                interface = iwlib.get_iwconfig(NETWORK_INTERFACE)
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
            today = date.today()
            todaysdate = today.strftime("%-d %B")
            weekday = today.strftime("%A")
            title =  "".join([str(todaysdate), " (", str(weekday),")"])
            message = "".join(["Week ", str(date.today().isocalendar()[1])])

        elif request == 'battery':
            title = "Battery status"
            message = str(subprocess.check_output(
                ["acpi"],
                shell = True), encoding = 'utf-8')

        return send_notification(title, message, timeout = 2500, urgent = False)
    
    return _notification

def toggle_microphone():
    """Run the toggle command and then send notification to report status of microphone"""
    def _toggle_microphone(qtile):
        if qtile:
            subprocess.call(['amixer set Capture toggle'], shell = True)

            message = subprocess.check_output(['amixer sget Capture'], shell = True).decode('utf-8')

            if re.search('off', message):
                message = "Muted"

            elif re.search('on', message):
                message = "Unmuted"

            title = "Microphone"

            send_notification(title, message, timeout = 2500, urgent = False)

        else:
            return

    return _toggle_microphone

def toggle_max_layout(qtile):
    """Basically trying to achieve a 'monocle' toggle of the focused window"""
    current_layout = qtile.current_group.layout.name

    if current_layout == "[]=":
        qtile.cmd_to_layout_index(1)

    elif current_layout == "[M]":
        qtile.cmd_to_layout_index(0)

def toggle_screen(qtile):
    """Move to next screen, and warp the mouse there as well"""
    qtile.cmd_next_screen()
    qtile.warp_to_screen()

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

        # Basically a focus toggle if two screens
        EzKey('M-a', lazy.function(toggle_screen)),

        # Various window controls
        EzKey('M-S-c', lazy.window.kill()),
        EzKey('M-n', lazy.layout.reset()),
        EzKey('M-<space>', lazy.function(toggle_max_layout)),
        EzKey('M-c', lazy.function(center_window)),
        EzKey('M-f', lazy.window.toggle_fullscreen()),
        EzKey('M-S-f', lazy.window.toggle_floating()),
        EzKey('M-S-<space>', lazy.layout.flip()),
        EzKey('M-<Tab>', lazy.spawn(SWITCHER)),
        EzKey('M-S-<Tab>', lazy.window.bring_to_front()),
        EzKey('M-b', lazy.hide_show_bar()),

        # Notification commands
        EzKey('M-S-b', lazy.function(notification('battery'))),
        EzKey('M-S-d', lazy.function(notification('date'))),
        EzKey('M-S-w', lazy.function(notification('wifi'))),


        # Some app shortcuts
        EzKey('M-w', lazy.function(run_or_raise(BROWSER))),
        EzKey('M-<Return>', lazy.spawn(TERMINAL)),
        EzKey('M-C-<Return>', lazy.spawn(FILE_MANAGER)),
        EzKey('M-c', lazy.function(run_or_raise('signal-desktop'))),
        EzKey('M-r', lazy.spawn(LAUNCHER)),
        EzKey('M-d', lazy.function(run_or_raise('discord'))),
        EzKey('M-s', lazy.function(run_or_raise('spotify'))),
        EzKey('M-g', lazy.function(run_or_raise('steam-native'))),
        EzKey('M-p', lazy.spawn('passmenu')),

        # KeyChords for some special actions
        KeyChord([MOD], 'k', [
            EzKey('c', lazy.spawn('rofi-confedit')),
            EzKey('q', lazy.spawn('alacritty -e vim ~/.config/qtile/')),
            EzKey('u', lazy.spawn('alacritty -e yay -Syu')),
        ]),

        # ScratchPad terminal
        EzKey('M-S-<Return>', lazy.group['scratchpad'].dropdown_toggle('term')),

        # Spotify controls, lacking real media keys on 65% keyboard
        EzKey('M-8', lazy.spawn(''.join([MUSIC_CTRL, 'PlayPause']))),
        EzKey('M-9', lazy.spawn(''.join([MUSIC_CTRL, 'Next']))),
        EzKey('M-7', lazy.spawn(''.join([MUSIC_CTRL, 'Previous']))),

        # Media volume keys
        EzKey('<XF86AudioMute>', lazy.widget['volumectrl'].mute()),
        EzKey('<XF86AudioLowerVolume>', lazy.widget['volumectrl'].decrease_vol()),
        EzKey('<XF86AudioRaiseVolume>', lazy.widget['volumectrl'].increase_vol()),

        # Microphone toggle muted/unmuted
        EzKey('M-q', lazy.function(toggle_microphone())),

        # System controls
        EzKey('M-l', lazy.spawn('lock')),
        EzKey('M-S-r', lazy.reload_config()),
        EzKey('M-C-r', lazy.restart()),
        EzKey('M-S-q', lazy.shutdown()),
        EzKey('M-C-<Escape>', lazy.spawn('poweroff')),

    ]
# Groups
group_settings = [
        ('1', {'label': "1", 'layout': 'monadtall'}),
        ('2', {'label': "2", 'layout': 'monadtall'}),
        ('3', {'label': "3", 'layout': 'monadtall'}),
        ('4', {'label': "4", 'layout': 'monadtall'}),
        ('5', {'label': "5", 'layout': 'monadtall'}),
        ('6', {'label': "6", 'layout': 'monadtall'}),
    ]

groups = [Group(name, **kwargs) for name, kwargs in group_settings]

for i in groups:
    keys.extend([
    Key([MOD], i.name, lazy.group[i.name].toscreen(toggle=True)),
    Key([MOD, 'shift'], i.name, lazy.window.togroup(i.name)),
    ])

# ScratchPad
groups.append(ScratchPad('scratchpad', [
        DropDown('term', TERMINAL,
        warp_pointer = False,
        height = 0.6,
        y = 0.2)
        ]))

# Layouts
layout_theme = {
        'border_width': 2,
        'border_focus': colors['main'],
        'border_normal': colors['separator'],
        }

layouts = [
        layout.MonadTall(
        **layout_theme,
        single_border_width = 0,
        name = "[]=", 
        ),
        layout.Max(
        name = "[M]"
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
        font = 'FiraCode Nerd Font',
        fontsize = 13,
        background = colors['background'],
        foreground = colors['text']
        )

extension_defaults = widget_defaults.copy()

# Widgets
widgets = [
            widget.Sep(
                padding = 2,
                foreground = colors['background'],
                ),
            widget.GroupBox(
                margin_x = 0,
                hide_unused = False,
                disable_drag = True,
                use_mouse_wheel = False,
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
            widget.TextBox(
                padding = 8,
                foreground = colors['separator'],
                fontsize = 12,
                text = "|"
                ),
            widget.CurrentLayout(
                padding = 8,
                foreground = colors['main']
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
            widget.Systray(
                padding = 14,
                background = colors['background']
                ),
            widget.Sep(
                foreground = colors['background'],
                background = colors['background'],
                padding = 10
                ),
            widget.TextBox(
                padding = 12,
                foreground = colors['main'],
                text = "墳"
                ),
            VolumeCtrl(
                background = colors['background'],
                padding = 0,
                ),
            widget.Sep(
                foreground = colors['background'],
                background = colors['background'],
                padding = 8
                ),
            widget.TextBox(
                padding = 12,
                foreground = colors['main'],
                text = "直"
                ),
            widget.Wlan(
                format = "{essid}",
                foreground = colors['text'],
                interface = NETWORK_INTERFACE,
                disconnected_message = "Disconnected",
                update_interval = 7,
                padding = 0,
                mouse_callbacks={'Button3': lambda: qtile.cmd_spawn(''.join([TERMINAL, \
                                                    ' -e nmtui'])),
                                 'Button1': lambda: qtile.cmd_simulate_keypress([MOD, 'shift'], "w")}
                ),
            widget.Sep(
                foreground = colors['background'],
                background = colors['background'],
                padding = 8
                ),
            widget.TextBox(
                padding = 12,
                foreground = colors['main'],
                text = ""
                ),
            widget.Clock(
                foreground = colors['text'],
                background = colors['background'],
                format = '%H:%M',
                padding = 0,
                mouse_callbacks = {'Button1': lambda: qtile.cmd_simulate_keypress([MOD, 'shift'], "d"),
                                   'Button3': lambda: qtile.cmd_spawn('python -m webbrowser https://kalender.se')
                }
                ),
            widget.Sep(
                padding = 10,
                foreground = colors['background'],
                background = colors['background']
                )
        ]

# Check if the computer is a laptop, and if it is add battery widget
if os.path.isfile('/usr/bin/acpi'):
    widgets.insert(-3, CustomBattery(
        padding = 8,
        foreground = colors['main'],
        background = colors['background'],
        ))
    widgets.insert(-3, widget.Battery(
        padding = 0,
        foreground = colors['text'],
        background = colors['background'],
        format = "{percent:2.0%}",
        mouse_callbacks = {'Button1': lambda: qtile.cmd_simulate_keypress([MOD, 'shift'], "b")}
        ))
    widgets.insert(-3, widget.Sep(
        foreground = colors['background'],
        background = colors['background'],
        padding = 8
        ))

# Bar
bar = bar.Bar(widgets = widgets, size = 26)

# Screens
screens = [Screen(top = bar)]

# Misc
dgroups_key_binder = None
dgroups_app_rules = []
follow_mouse_focus = True
bring_front_click = True
cursor_warp = False
reconfigure_screens = True
auto_fullscreen = True
auto_minimize = True
focus_on_window_activation = 'urgent'
wmname = "LG3D"