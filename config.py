"""Qtile config a la stefur"""

from __future__ import annotations

import os
import subprocess

from datetime import datetime
from typing import TYPE_CHECKING
import iwlib  # type: ignore
import psutil  # type: ignore

from libqtile.config import (
    Key,
    Screen,
    Group,
    Drag,
    Click,
    Match,
    EzKey,
    KeyChord,
    ScratchPad,
    DropDown,
)
from libqtile.lazy import lazy
from libqtile import layout, bar, widget, hook, qtile
from libqtile.utils import send_notification
from libqtile.backend.base import Window

from battery import CustomBattery
from spotify import NowPlaying
from volume import VolumeCtrl
from wifi import Wifi
from colors import colors

if TYPE_CHECKING:
    from typing import Any, Dict, List, Optional, Set, Tuple, Union
    from libqtile.core.manager import Qtile

MOD = "mod4"

modifier_keys: Dict[str, str] = {
    "M": "mod4",
    "A": "mod1",
    "C": "control",
    "S": "shift",
}

network_interfaces: List[str] = os.listdir("/sys/class/net")
wifi_prefix: Tuple[str, ...] = ("wlp", "wlan")

for interface in network_interfaces:
    if interface.startswith(wifi_prefix):
        WIFI_INTERFACE = interface
        break

TERMINAL = "alacritty"
BROWSER = "firefox"
LAUNCHER = (
    "rofi -no-lazy-grab -show drun -modi drun -theme ~/.config/rofi/style_launcher"
)
SWITCHER = "rofi -show window -modi window -theme ~/.config/rofi/style_switcher"
FILE_MANAGER = "pcmanfm"
MUSIC_CTRL = "dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player."

font_setting: Tuple[str, int] = ("FiraCode Nerd Font Regular", 13)

HAS_BATTERY: bool = os.path.isdir("/sys/class/power_supply/BAT0")

group_assignments: Dict[str, Any[str, ...]] = {
    "1": ("firefox"),
    "2": (
        "valheim.x86_64",
        "battle.net.exe",
        "wowclassic.exe",
        "ck3",
        "paradox launcher",
        "steam_app",
    ),
    "3": ("discord", "signal"),
    "4": ("spotify"),
    "5": ("Steam"),
}


@hook.subscribe.startup_once
def autostart() -> None:
    """Autostart things from script when qtile starts and hide the bar as default"""
    with subprocess.Popen("autostart.sh", shell=True) as process:
        hook.subscribe.shutdown(process.terminate)


@hook.subscribe.client_name_updated
def follow_url(client: Window) -> None:
    """If Firefox is flagged as urgent, focus it"""
    wm_class: list | None = client.get_wm_class()
    assert wm_class is not None
    for item in wm_class:
        if BROWSER in item and client.urgent is True:
            assert qtile and client.group is not None
            qtile.current_screen.set_group(client.group)
            client.group.focus(client)


@hook.subscribe.float_change
def center_window() -> None:
    """Centers all the floating windows"""
    try:
        assert qtile is not None
        qtile.current_window.cmd_center()
    except AttributeError:
        return


@hook.subscribe.client_new
def assign_app_group(client: Window) -> None:
    """Decides which apps go where when they are launched"""
    try:
        wm_class = client.get_wm_class()
        assert wm_class is not None
        for group, apps in group_assignments.items():
            if any(item.startswith(apps) for item in wm_class):
                client.togroup(group)
    except IndexError:
        return


@hook.subscribe.client_new
def toggle_fullscreen_off(client: Window) -> None:
    """Toggle fullscreen off in case there's any window fullscreened in the group"""
    try:
        group = client.group
    except AttributeError:
        return

    if group is None:
        assert qtile is not None
        group = qtile.current_group

    for window in group.windows:
        if window.fullscreen:
            window.toggle_fullscreen()


@hook.subscribe.client_name_updated
def push_spotify(client: Window) -> None:
    """Push Spotify to correct group since it's wm_class setting is slow"""
    if client.cmd_info().get("name") == "Spotify" and not client.get_wm_class():
        client.cmd_togroup("4")


@hook.subscribe.client_killed
def fallback_default_layout(client: Window) -> None:
    """Reset a group to default layout when theres is only one window left"""
    try:
        assert client.group is not None
        win_count = len(client.group.windows)
    except AttributeError:
        win_count = 0

    if win_count > 2:
        return

    try:
        assert client.group is not None
        screen = client.group.screen
    except AttributeError:
        return

    if screen is None:
        assert qtile is not None
        screen = qtile.current_group.screen

    screen_rect = screen.get_rect()
    client.group.layout.hide()
    client.group.cmd_setlayout(layout_names["monadtall"])
    client.group.layout.show(screen_rect)


@hook.subscribe.client_killed
def minimize_discord(client: Window) -> None:
    """Discord workaround to fix lingering residual window after its been closed to tray"""
    wm_class: list | None = client.get_wm_class()
    assert wm_class is not None
    for item in wm_class:
        if "discord" in item:
            client.cmd_toggle_floating()
            client.cmd_toggle_minimize()


@hook.subscribe.current_screen_change
def warp_cursor() -> None:
    """Warp cursor to focused screen"""
    assert qtile is not None
    qtile.warp_to_screen()


@lazy.function
def spawn_or_focus(qtile: Qtile, app: str) -> None:
    """Check if the app being launched is already running, if so focus it"""
    window = None
    for win in qtile.windows_map.values():
        if isinstance(win, Window):
            wm_class = win.get_wm_class()
            assert wm_class is not None
            if any(item.lower() in app for item in wm_class):
                window = win
                group = win.group
                assert group is not None
                group.cmd_toscreen(toggle=False)
                break

    if window is None:
        qtile.cmd_spawn(app)
        return

    if window == qtile.current_window:
        try:
            qtile.current_layout.cmd_swap_main()
        except AttributeError:
            return
    else:
        qtile.current_group.focus(window)


@lazy.function
def float_to_front(qtile: Qtile) -> None:
    """Bring all floating windows of the group to front"""
    for window in qtile.current_group.windows:
        if window.floating:
            window.cmd_bring_to_front()


@lazy.function
def clear_urgent(qtile: Qtile) -> None:
    """Clear the urgent flags for windows in a group"""
    groupbox = qtile.widgets_map.get("groupbox")
    assert groupbox is not None
    group = groupbox.get_clicked_group()
    for window in group.windows:
        if window.urgent:
            window.urgent = False
    groupbox.draw()


@lazy.function
def notification(qtile: Qtile, request: str) -> None:
    """Used for mouse callbacks and keybinds to send notifications"""
    if request == "wifi":
        try:
            iface = iwlib.get_iwconfig(WIFI_INTERFACE)
            quality = iface["stats"]["quality"]
            quality = round((quality / 70) * 100)
            ssid = str(iface["ESSID"], encoding="utf-8")
            title = "Wifi"
            message = f"{ssid}\nSignal strength: {quality}%"
        except KeyError:
            title = "Disconnected"
            message = ""

    elif request == "date":
        today = datetime.today()
        todaysdate = today.strftime("%-d %B")
        weekday = today.strftime("%A")
        week = datetime.today().isocalendar()[1]
        title = f"{todaysdate}, ({weekday})"
        message = f"Week {week}"

    elif request == "time":
        now = datetime.now()
        title = "The time is:"
        message = now.strftime("%H:%M")

    elif request == "battery":
        if HAS_BATTERY:
            battery = psutil.sensors_battery()
            title = "Battery"
            message = f"{round(battery.percent)}%"
        else:
            return

    send_notification(title, message, timeout=2500, urgent=False)


@lazy.function
def toggle_microphone(qtile: Qtile) -> None:
    """Run the toggle command and then send notification to report status of microphone"""
    try:
        subprocess.call(["amixer set Capture toggle"], shell=True)

        message = subprocess.check_output(["amixer sget Capture"], shell=True).decode(
            "utf-8"
        )

        if "off" in message:
            message = "Muted"

        elif "on" in message:
            message = "Unmuted"

        title = "Microphone"
        send_notification(title, message, timeout=2500, urgent=False)

    except subprocess.CalledProcessError:
        return


@lazy.function
def toggle_layout(qtile: Qtile, layout_name: str) -> None:
    """Takes a layout name and tries to set it, or if it's already active back to monadtall"""
    screen_rect = qtile.current_group.screen.get_rect()
    qtile.current_group.layout.hide()
    if qtile.current_group.layout.name == layout_name:
        qtile.current_group.cmd_setlayout(layout_names["monadtall"])
    else:
        qtile.current_group.cmd_setlayout(layout_name)
    qtile.current_group.layout.show(screen_rect)


# Layouts
layout_theme: Dict[str, int | str] = {
    "border_width": 2,
    "border_focus": colors["primary"],
    "border_normal": colors["secondary"],
}

layout_names: Dict[str, str] = {"monadtall": "tall~", "max": "max~", "treetab": "tree~"}

layouts = [
    layout.MonadTall(
        **layout_theme, single_border_width=0, name=layout_names["monadtall"]
    ),
    layout.Max(name=layout_names["max"]),
    layout.TreeTab(
        name=layout_names["treetab"],
        font=font_setting[0],
        fontsize=font_setting[1],
        active_fg=colors["background"],
        active_bg=colors["primary"],
        bg_color=colors["background"],
        border_width=5,
        inactive_bg=colors["secondary"],
        inactive_fg=colors["text"],
        previous_on_rm=True,
        urgent_fg=colors["urgent"],
        urgent_bg=colors["secondary"],
        sections=[""],
        section_fg=colors["background"],
        padding_left=10,
        padding_y=8,
        margin_y=10,
    ),
]

floating_layout = layout.Floating(
    float_rules=[
        *layout.Floating.default_float_rules,
        Match(wm_class="Nm-connection-editor"),
        Match(wm_class="pinentry-gtk-2"),
        Match(wm_class="Lxappearance"),
        Match(wm_class="Xfce4-taskmanager"),
        Match(wm_class="VirtualBox Manager"),
        Match(wm_class="pavucontrol"),
        Match(
            title="Confirm File Replacing"
        ),  # This is to float the copy/replace dialog of Pcmanfm
    ],
    **layout_theme,
)

# Keybinds
keys = [
    # Switch focus between windows
    EzKey("M-<Down>", lazy.layout.down()),
    EzKey("M-<Up>", lazy.layout.up()),
    EzKey("M-<Left>", lazy.layout.left().when(layout=layout_names["monadtall"])),
    EzKey("M-<Right>", lazy.layout.right().when(layout=layout_names["monadtall"])),
    # Move windows between left/right columns or move up/down in current stack
    EzKey("M-S-<Left>", lazy.layout.swap_left().when(layout=layout_names["monadtall"])),
    EzKey(
        "M-S-<Right>", lazy.layout.swap_right().when(layout=layout_names["monadtall"])
    ),
    EzKey(
        "M-S-<Down>",
        lazy.layout.shuffle_down().when(layout=layout_names["monadtall"]),
        lazy.layout.move_down().when(layout=layout_names["treetab"]),
    ),
    EzKey(
        "M-S-<Up>",
        lazy.layout.shuffle_up().when(layout=layout_names["monadtall"]),
        lazy.layout.move_up().when(layout=layout_names["treetab"]),
    ),
    # Grow/shrink windows
    EzKey(
        "M-C-<Left>", lazy.layout.shrink_main().when(layout=layout_names["monadtall"])
    ),
    EzKey(
        "M-C-<Right>", lazy.layout.grow_main().when(layout=layout_names["monadtall"])
    ),
    EzKey("M-C-<Down>", lazy.layout.shrink().when(layout=layout_names["monadtall"])),
    EzKey("M-C-<Up>", lazy.layout.grow().when(layout=layout_names["monadtall"])),
    # Move between screens
    EzKey("M-<period>", lazy.next_screen()),
    EzKey("M-<comma>", lazy.prev_screen()),
    # Various window controls
    EzKey("M-S-c", lazy.window.kill()),
    EzKey("M-C-c", lazy.window.center()),
    EzKey("M-S-<space>", lazy.layout.reset()),
    EzKey("M-f", lazy.window.toggle_fullscreen()),
    EzKey("M-S-f", lazy.window.toggle_floating()),
    EzKey("M-<space>", lazy.layout.flip()),
    EzKey("M-<Tab>", lazy.spawn(SWITCHER)),
    EzKey("M-S-<Tab>", float_to_front()),
    EzKey("M-b", lazy.hide_show_bar()),
    # Layout toggles
    EzKey("M-m", toggle_layout(layout_names["max"])),
    EzKey("M-t", toggle_layout(layout_names["treetab"])),
    # Notification commands
    EzKey("M-S-b", notification("battery")),
    EzKey("M-S-d", notification("date")),
    EzKey("M-S-w", notification("wifi")),
    EzKey("M-S-t", notification("time")),
    # Some app shortcuts
    EzKey("M-w", spawn_or_focus(BROWSER)),
    EzKey("M-<Return>", lazy.spawn(TERMINAL)),
    EzKey("M-C-<Return>", lazy.spawn(FILE_MANAGER)),
    EzKey("M-c", spawn_or_focus("signal-desktop")),
    EzKey("M-r", lazy.spawn(LAUNCHER)),
    EzKey("M-d", spawn_or_focus("discord")),
    EzKey("M-s", spawn_or_focus("spotify")),
    EzKey("M-g", spawn_or_focus("steam-native")),
    EzKey("M-p", lazy.spawn("passmenu.sh")),
    # KeyChords for some special actions
    KeyChord(
        [MOD],
        "k",
        [
            EzKey("c", lazy.spawn("confedit.sh")),
            EzKey("q", lazy.spawn(f"{TERMINAL} -e vim ~/.config/qtile/")),
            EzKey("u", lazy.spawn(f"{TERMINAL} -e yay -Syu")),
            EzKey("b", lazy.spawn(f"{TERMINAL} -e bluetoothctl")),
        ],
    ),
    # ScratchPads
    EzKey("M-S-<Return>", lazy.group["scratchpad"].dropdown_toggle("terminal")),
    EzKey("M-n", lazy.group["scratchpad"].dropdown_toggle("newsboat")),
    # Spotify controls, lacking real media keys on 65% keyboard
    EzKey("M-8", lazy.spawn(f"{MUSIC_CTRL}PlayPause")),
    EzKey("M-9", lazy.spawn(f"{MUSIC_CTRL}Next")),
    EzKey("M-7", lazy.spawn(f"{MUSIC_CTRL}Previous")),
    # Media volume keys
    EzKey("<XF86AudioMute>", lazy.widget["volumectrl"].mute()),
    EzKey("M-S-m", lazy.widget["volumectrl"].mute()),  # Extra keybind
    EzKey("<XF86AudioLowerVolume>", lazy.widget["volumectrl"].decrease_vol()),
    EzKey("<XF86AudioRaiseVolume>", lazy.widget["volumectrl"].increase_vol()),
    # Microphone toggle muted/unmuted
    EzKey("M-q", toggle_microphone()),
    # System controls
    EzKey("M-l", lazy.spawn("lock.sh")),
    EzKey("M-S-r", lazy.reload_config()),
    EzKey("M-C-r", lazy.restart()),
    EzKey("M-S-q", lazy.shutdown()),
    EzKey("M-C-<Escape>", lazy.spawn("poweroff")),
]

# Groups
group_settings: List[Tuple[str, Dict[str, Any]]] = [
    ("1", {"label": "1", "layout": layout_names["monadtall"]}),
    ("2", {"label": "2", "layout": layout_names["monadtall"]}),
    ("3", {"label": "3", "layout": layout_names["monadtall"]}),
    ("4", {"label": "4", "layout": layout_names["monadtall"]}),
    ("5", {"label": "5", "layout": layout_names["monadtall"]}),
    ("6", {"label": "6", "layout": layout_names["monadtall"]}),
]

groups: List[Any] = [Group(name, **kwargs) for name, kwargs in group_settings]

for i in groups:
    keys.extend(
        [
            Key([MOD], i.name, lazy.group[i.name].toscreen(toggle=True)),
            Key([MOD, "shift"], i.name, lazy.window.togroup(i.name)),
        ]
    )

# ScratchPads
groups.append(
    ScratchPad(
        "scratchpad",
        [
            DropDown(
                "terminal", TERMINAL, warp_pointer=False, height=0.6, y=0.2, opacity=1
            ),
            DropDown(
                "newsboat",
                f"{TERMINAL} -e newsboat",
                warp_pointer=False,
                height=0.6,
                y=0.2,
                opacity=1,
            ),
        ],
    )
)

# Mouse
mouse = [
    Drag(
        [MOD],
        "Button1",
        lazy.window.set_position_floating(),
        start=lazy.window.get_position(),
    ),
    Drag(
        [MOD], "Button3", lazy.window.set_size_floating(), start=lazy.window.get_size()
    ),
    Click([MOD], "Button2", lazy.window.toggle_floating()),
]

# Widgets & extension defaults
widget_defaults = dict(
    font=font_setting[0],
    fontsize=font_setting[1],
    background=colors["background"],
    foreground=colors["text"],
)

extension_defaults = widget_defaults.copy()

# Widgets
widgets = [
    widget.GroupBox(
        margin_x=0,
        hide_unused=False,
        disable_drag=True,
        use_mouse_wheel=False,
        padding=6,
        borderwidth=3,
        active=colors["primary"],
        inactive=colors["secondary"],
        rounded=False,
        highlight_color=colors["background"],
        block_highlight_text_color=colors["background"],
        highlight_method="block",
        this_current_screen_border=colors["primary"],
        this_screen_border=colors["primary"],
        foreground=colors["text"],
        urgent_alert_method="text",
        urgent_text=colors["urgent"],
        mouse_callbacks={"Button3": clear_urgent()},
    ),
    widget.CurrentLayout(padding=8, foreground=colors["primary"]),
    widget.WindowName(
        max_chars=50,
        empty_group_string="Desktop",
    ),
    NowPlaying(
        mouse_callbacks={
            "Button1": lazy.spawn(f"{MUSIC_CTRL}PlayPause"),
            "Button3": spawn_or_focus("spotify"),
        }
    ),
    widget.Systray(padding=12, background=colors["background"]),
    widget.Sep(
        foreground=colors["background"], background=colors["background"], padding=8
    ),
    widget.TextBox(padding=12, foreground=colors["primary"], text=""),
    widget.Clock(
        foreground=colors["text"],
        background=colors["background"],
        format="%H:%M",
        padding=0,
        mouse_callbacks={
            "Button1": notification("date"),
            "Button3": lazy.spawn("python -m webbrowser https://kalender.se"),
        },
    ),
    widget.Sep(
        padding=10, foreground=colors["background"], background=colors["background"]
    ),
]

# Check if this is my laptop, and add some widgets if it is
if HAS_BATTERY:
    widgets.insert(
        -3, widget.TextBox(padding=12, foreground=colors["primary"], text="墳")
    )
    widgets.insert(
        -3,
        VolumeCtrl(
            background=colors["background"],
            padding=0,
        ),
    )
    widgets.insert(
        -3,
        widget.Sep(
            foreground=colors["background"], background=colors["background"], padding=16
        ),
    )
    widgets.insert(
        -3,
        Wifi(
            foreground=colors["primary"],
            padding=0,
            mouse_callbacks={
                "Button3": lazy.spawn(f"{TERMINAL} -e nmtui"),
                "Button1": notification("wifi"),
            },
        ),
    )
    widgets.insert(
        -3,
        widget.Sep(
            foreground=colors["background"], background=colors["background"], padding=16
        ),
    )
    widgets.insert(
        -3,
        CustomBattery(
            padding=0,
            foreground=colors["primary"],
            background=colors["background"],
            mouse_callbacks={"Button1": notification("battery")},
        ),
    )
    widgets.insert(
        -3,
        widget.Sep(
            foreground=colors["background"], background=colors["background"], padding=8
        ),
    )

# Bar
bar = bar.Bar(widgets=widgets, size=26)

# Screens
screens = [Screen(top=bar)]

# Misc
dgroups_key_binder = None
dgroups_app_rules = []  # type: List
follow_mouse_focus = True
bring_front_click = True
cursor_warp = False
reconfigure_screens = True
auto_fullscreen = True
auto_minimize = True
focus_on_window_activation = "urgent"
wmname = "LG3D"
