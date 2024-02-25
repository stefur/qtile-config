"""qtile wayland config"""

from __future__ import annotations

import os
import subprocess

from typing import TYPE_CHECKING

from libqtile.config import (
    Key,
    Screen,
    Group,
    Drag,
    Click,
    Match,
    ScratchPad,
    DropDown,
)
from libqtile.lazy import lazy
from libqtile import hook, qtile
from libqtile.backend.wayland import InputConfig

from libqtile.layout.max import Max
from libqtile.layout.xmonad import MonadTall
from libqtile.layout.tree import TreeTab
from libqtile.layout.floating import Floating

from libqtile.backend.base import Window
from libqtile.group import _Group

from colors import colors

if TYPE_CHECKING:
    from typing import Any
    from libqtile.core.manager import Qtile

assert qtile is not None, "This should never be None."

MOD = "mod4"
ALT = "mod1"
TERMINAL = "foot"
BROWSER = "firefox"
LAUNCHER = "fuzzel.sh"
FILE_MANAGER = "pcmanfm"
MUSIC_CTRL = """dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify
 /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player."""

font_setting: tuple[str, int] = ("FiraMono Nerd Font", 13)

group_assignments: dict[str, Any[str, ...]] = {
    "1": (BROWSER),
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

# Inputs configuration
wl_input_rules = {
    "type:keyboard": InputConfig(
        kb_repeat_rate=50,
        kb_repeat_delay=300,
    ),
    "type:touchpad": InputConfig(drag=True, tap=True, natural_scroll=True),
}

home = os.path.expandvars("$HOME")
wallpapers = os.listdir(f"{home}/wallpapers")
random_wallpaper = random.choice(wallpapers)
path_to_wallpaper = os.path.join(f"{home}/wallpapers", random_wallpaper)

startup_items = [
    f"waybar -c {home}/.config/waybar/config-qtile &",
    "wlsunset -l 59.6 -L 18.1 &",
    f"swaybg -m fill -i {path_to_wallpaper} &",
    f"convert {path_to_wallpaper} -blur 16x8 /tmp/lock_img.jpg &",
    "syncthing &",
    "pipewire &",
    "mako &",
    "kanshi &",
    "swayidle -w timeout 300 'lock.sh' timeout 600 'wlopm --off '*'' resume 'wlopm --on '*'' timeout 900 'loginctl suspend' before-sleep 'lock.sh' &",
    "gpg-connect-agent &",
    "/usr/libexec/polkit-gnome-authentication-agent-1 &",
    "dbus-update-activation-environment DISPLAY",
]


@hook.subscribe.startup_once
def autostart() -> None:
    """Autostart things when qtile starts"""

    subprocess.call(["brightnessctl set 20%"], shell=True)

    for item in startup_items:
        with subprocess.Popen(item, shell=True) as process:
            hook.subscribe.shutdown(process.terminate)


class GroupState(Enum):
    EMPTY = 1
    OCCUPIED = 2
    FOCUSED = 3


@hook.subscribe.focus_change
@hook.subscribe.client_killed
@hook.subscribe.client_managed
def update_groups_waybar(*_args) -> None:
    """Update Waybar of open groups and windows"""
    existing_groups = dict.fromkeys(qtile.groups_map.keys(), GroupState.EMPTY)  # type: ignore[attr-defined]

    existing_groups.pop("scratchpad", None)

    current_group: str = qtile.current_screen.group.label  # type: ignore[attr-defined]

    for window in qtile.windows():  # type: ignore[attr-defined]
        if (
            window["wm_class"] is not None
            and window["group"] is not None
            and window["group"] in existing_groups
        ):
            existing_groups[window["group"]] = GroupState.OCCUPIED

    existing_groups[current_group] = GroupState.FOCUSED

    text: str = ""

    for group, status in existing_groups.items():
        match status:
            case GroupState.OCCUPIED:
                text += f"""<span fgcolor='{colors["primary"]}'> {group} </span>"""
            case GroupState.EMPTY:
                text += f"""<span fgcolor='{colors["secondary"]}'> {group} </span>"""
            case GroupState.FOCUSED:
                text += f"""<span fgcolor='{colors["background"]}' bgcolor='{colors["primary"]}' line_height='2'> {group} </span>"""

    with open("/tmp/qtile-groups.txt", "w", encoding="utf-8") as output:
        output.write(text)
        output.close()

    subprocess.call(["pkill -RTMIN+8 waybar"], shell=True)


@hook.subscribe.focus_change
def update_window_title_waybar() -> None:
    """Update Waybar of focused window title"""
    window_title: str = (
        "" if qtile.current_window is None else qtile.current_window.name  # type: ignore[attr-defined]
    )

    with open("/tmp/qtile-window-title.txt", "w", encoding="utf-8") as output:
        output.write(f"<span fgcolor='{colors["text"]}'>{window_title}</span>")
        output.close()

    subprocess.call(["pkill -RTMIN+9 waybar"], shell=True)


@hook.subscribe.startup_complete
@hook.subscribe.layout_change
def update_layout_waybar(*_args) -> None:
    """Update Waybar of current layout"""
    try:
        current_layout = qtile.current_layout.name  # type: ignore[attr-defined]
    except AttributeError:
        current_layout = ""

    with open("/tmp/qtile-layout.txt", "w", encoding="utf-8") as output:
        output.write(f"<span fgcolor='{colors["primary"]}'>{current_layout}</span>")
        output.close()

    subprocess.call(["pkill -RTMIN+7 waybar"], shell=True)


@hook.subscribe.client_urgent_hint_changed
def follow_url(client: Window) -> None:
    """If Firefox is flagged as urgent, focus it"""

    wm_class: list | None = client.get_wm_class()

    if wm_class is not None:
        for item in wm_class:
            match item:
                case item if item.lower() in BROWSER and client.group is not None:
                    qtile.current_screen.set_group(client.group)  # type: ignore[attr-defined]
                    client.group.focus(client)
                    return


@hook.subscribe.float_change
def center_window() -> None:
    """Centers all the floating windows"""

    try:
        if qtile.current_window is not None:  # type: ignore[attr-defined]
            qtile.current_window.center()  # type: ignore[attr-defined]
    except AttributeError:
        return


@hook.subscribe.layout_change
def max_win_count(new_layout: MonadTall | Max | TreeTab, group: _Group) -> None:
    """Displays the window counter if the max layout is used"""
    del group  # Unused parameter

    try:
        wincount_widget = qtile.widgets_map.get("windowcount")  # type: ignore[attr-defined]

        if new_layout.name == layout_names["max"]:
            wincount_widget.foreground = colors["primary"]
            wincount_widget.padding = 0
        else:
            wincount_widget.foreground = colors["background"]
            wincount_widget.padding = -12
    except AttributeError:
        return


@hook.subscribe.client_new
def assign_app_group(client: Window) -> None:
    """Decides which apps go where when they are launched"""
    wm_class: list | None = client.get_wm_class()
    if wm_class is None:
        return

    try:
        for group, apps in group_assignments.items():
            if any(item.lower().startswith(apps) for item in wm_class):
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
        group = qtile.current_group  # type: ignore[attr-defined]

    for window in group.windows:
        if window.fullscreen:
            window.toggle_fullscreen()


@hook.subscribe.client_killed
def fallback_default_layout(client: Window) -> None:
    """Reset a group to default layout when theres is only one window left"""

    if (
        not isinstance(client, Window)
        or client.group is None
        or client.group.screen != qtile.current_screen  # type: ignore[attr-defined]
        or client.floating is True
    ):
        return

    try:
        win_count = len(client.group.windows)
    except AttributeError:
        win_count = 0

    if win_count > 1:
        return

    group_name: str = client.group.name
    default_layout_index: int = 0

    qtile.to_layout_index(default_layout_index, group_name)  # type: ignore[attr-defined]


@hook.subscribe.current_screen_change
def warp_cursor() -> None:
    """Warp cursor to focused screen"""
    qtile.warp_to_screen()  # type: ignore[attr-defined]


def spawn_or_focus(self: Qtile, app: str) -> None:
    """Check if the app being launched is already running, if so focus it"""
    window = None
    for win in self.windows_map.values():
        if isinstance(win, Window):
            wm_class: list | None = win.get_wm_class()
            if wm_class is None or win.group is None:
                return
            if any(item.lower() in app.lower() for item in wm_class):
                window = win
                group = win.group
                group.toscreen(toggle=False)
                break

    if window is None:
        self.spawn(app)

    elif window == self.current_window:
        try:
            assert (
                self.current_layout.swap_main is not None
            ), "The current layout should have swap_main"
            self.current_layout.swap_main()
        except AttributeError:
            return
    else:
        self.current_group.focus(window)


def float_to_front(self: Qtile) -> None:
    """Bring all floating windows of the group to front"""
    for window in self.current_group.windows:
        if window.floating:
            window.bring_to_front()


def toggle_layout(self: Qtile, layout_name: str) -> None:
    """Takes a layout name and tries to set it, or if it's already active back to monadtall"""
    assert (
        self.current_group.screen is not None
    ), "The screen should not be none for the current group"
    screen_rect = self.current_group.screen.get_rect()
    self.current_group.layout.hide()
    if self.current_group.layout.name == layout_name:
        self.current_group.setlayout(layout_names["monadtall"])
    else:
        self.current_group.setlayout(layout_name)
    self.current_group.layout.show(screen_rect)


def next_window(self: Qtile) -> None:
    """If treetab or max layout, cycle next window"""
    if self.current_layout.name in (layout_names["max"], layout_names["treetab"]):
        self.current_group.layout.down()


def focus_group(self: Qtile, direction: str) -> None:
    """Go to next/previous group"""
    group: _Group = self.current_screen.group

    go_to: _Group

    match direction:
        case "next":
            go_to = group.get_next_group(skip_empty=False)
        case "previous":
            go_to = group.get_previous_group(skip_empty=False)
        case _:
            return

    self.current_screen.set_group(go_to)


def window_to_screen(self: Qtile, direction: str) -> None:
    """Send a window to next/previous screen"""
    screen_i: int = self.screens.index(self.current_screen)

    if screen_i != 0 and self.current_window is not None:
        group: str

        match direction:
            case "next":
                group = self.screens[screen_i + 1].group.name
            case "previous":
                group = self.screens[screen_i - 1].group.name

        self.current_window.togroup(group)


# Layouts
layout_theme: dict[str, int | str] = {
    "border_width": 3,
    "border_focus": colors["primary"],
    "border_normal": colors["secondary"],
}

layout_names: dict[str, str] = {"monadtall": "tall~", "max": "max~", "treetab": "tree~"}

layouts = [
    MonadTall(
        **layout_theme,
        single_border_width=0,
        single_margin=0,
        margin=10,
        new_client_position="top",
        name=layout_names["monadtall"],
    ),
    Max(name=layout_names["max"]),
    TreeTab(
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
        margin_y=0,
    ),
]

floating_layout = Floating(
    float_rules=[
        *Floating.default_float_rules,
        Match(wm_class="Pinentry-gtk-2"),
        Match(wm_class="pavucontrol"),
        Match(title="Execute File", wm_class="Pcmanfm"),
        Match(title="Confirm File Replacing", wm_class="Pcmanfm"),
        Match(title="Steam", wm_class=""),
    ],
    **layout_theme,
)

# Keybinds
keys = [
    # Switch focus between windows
    Key([MOD], "Down", lazy.layout.down()),
    Key([MOD], "Up", lazy.layout.up()),
    Key([MOD], "Left", lazy.layout.left().when(layout=layout_names["monadtall"])),
    Key([MOD], "Right", lazy.layout.right().when(layout=layout_names["monadtall"])),
    # Move windows between left/right columns or move up/down in current stack
    Key(
        [MOD, "shift"],
        "Left",
        lazy.layout.swap_left().when(layout=layout_names["monadtall"]),
    ),
    Key(
        [MOD, "shift"],
        "Right",
        lazy.layout.swap_right().when(layout=layout_names["monadtall"]),
    ),
    Key(
        [MOD, "shift"],
        "Down",
        lazy.layout.shuffle_down().when(layout=layout_names["monadtall"]),
        lazy.layout.move_down().when(layout=layout_names["treetab"]),
    ),
    Key(
        [MOD, "shift"],
        "Up",
        lazy.layout.shuffle_up().when(layout=layout_names["monadtall"]),
        lazy.layout.move_up().when(layout=layout_names["treetab"]),
    ),
    # Grow/shrink windows
    Key(
        [MOD, ALT],
        "Left",
        lazy.layout.shrink_main().when(layout=layout_names["monadtall"]),
    ),
    Key(
        [MOD, ALT],
        "Right",
        lazy.layout.grow_main().when(layout=layout_names["monadtall"]),
    ),
    Key(
        [MOD, ALT], "Down", lazy.layout.shrink().when(layout=layout_names["monadtall"])
    ),
    Key([MOD, ALT], "Up", lazy.layout.grow().when(layout=layout_names["monadtall"])),
    # Move focus/windows between screens
    Key([MOD], "Tab", lazy.screen.toggle_group()),
    Key([MOD], "period", lazy.next_screen()),
    Key([MOD], "comma", lazy.prev_screen()),
    Key([MOD, "shift"], "period", lazy.function(window_to_screen, "next")),
    Key([MOD, "shift"], "comma", lazy.function(window_to_screen, "previous")),
    Key([MOD, "control"], "Right", lazy.function(focus_group, "next")),
    Key([MOD, "control"], "Left", lazy.function(focus_group, "previous")),
    # Various window controls
    Key([MOD, "shift"], "c", lazy.window.kill()),
    Key([MOD, "control"], "c", lazy.window.center()),
    Key([MOD, "shift"], "space", lazy.layout.reset()),
    Key([MOD], "f", lazy.window.toggle_fullscreen()),
    Key([MOD, "shift"], "f", lazy.window.toggle_floating()),
    Key([MOD], "space", lazy.layout.flip()),
    Key([MOD, "shift"], "Tab", lazy.function(float_to_front)),
    Key([MOD], "b", lazy.hide_show_bar()),
    Key([MOD], "u", lazy.clear_urgent("keybind")),
    Key([MOD], "i", lazy.toggle_widget_info()),
    # Layout toggles
    Key([MOD], "m", lazy.function(toggle_layout, layout_names["max"])),
    Key([MOD], "t", lazy.function(toggle_layout, layout_names["treetab"])),
    # Notification commands
    Key([MOD, "shift"], "b", lazy.spawn("callbacks.sh battery")),
    Key([MOD, "shift"], "d", lazy.spawn("callbacks.sh date")),
    Key([MOD, "shift"], "w", lazy.spawn("callbacks.sh wifi")),
    # Some app shortcuts
    Key([MOD], "w", lazy.function(spawn_or_focus, BROWSER)),
    Key([MOD], "Return", lazy.spawn(TERMINAL)),
    Key([MOD, "control"], "Return", lazy.spawn(FILE_MANAGER)),
    Key([MOD], "c", lazy.function(spawn_or_focus, "signal-desktop")),
    Key([MOD], "r", lazy.spawn(LAUNCHER)),
    Key([MOD], "d", lazy.function(spawn_or_focus, "Discord")),
    Key([MOD], "s", lazy.function(spawn_or_focus, "spotify")),
    Key([MOD], "g", lazy.function(spawn_or_focus, "steam-native")),
    Key([MOD], "p", lazy.spawn("pass.sh")),
    Key([MOD, "control"], "m", lazy.spawn("mount.sh")),
    Key([MOD], "e", lazy.spawn("emojis.sh")),
    Key([MOD, "shift"], "p", lazy.spawn("screenshot.sh")),
    # ScratchPads
    Key([MOD, "shift"], "Return", lazy.group["scratchpad"].dropdown_toggle("terminal")),
    Key([MOD], "n", lazy.group["scratchpad"].dropdown_toggle("newsboat")),
    Key([MOD], "Escape", lazy.group["scratchpad"].hide_all()),
    # Spotify controls, lacking real media keys on 65% keyboard
    Key([MOD], "8", lazy.spawn(f"{MUSIC_CTRL}PlayPause")),
    Key([MOD], "9", lazy.spawn(f"{MUSIC_CTRL}Next")),
    Key([MOD], "7", lazy.spawn(f"{MUSIC_CTRL}Previous")),
    # Media volume keys
    Key([], "XF86AudioMute", lazy.widget["volumectrl"].adjust_volume("mute")),
    Key(
        [MOD, "shift"], "m", lazy.widget["volumectrl"].adjust_volume("mute")
    ),  # Extra keybind
    Key(
        [], "XF86AudioLowerVolume", lazy.widget["volumectrl"].adjust_volume("decrease")
    ),
    Key(
        [], "XF86AudioRaiseVolume", lazy.widget["volumectrl"].adjust_volume("increase")
    ),
    # Brightness controll
    Key([], "XF86MonBrightnessDown", lazy.spawn("brightnessctl set 5%-")),
    Key([], "XF86MonBrightnessUp", lazy.spawn("brightnessctl set +5%")),
    # Microphone toggle muted/unmuted
    Key([MOD], "q", lazy.spawn("callbacks.sh mic")),
    # System controls
    Key([MOD], "l", lazy.spawn("lock.sh")),
    Key([MOD, "shift"], "r", lazy.reload_config()),
    Key([MOD, "control"], "r", lazy.restart()),
    Key([MOD, "shift"], "q", lazy.shutdown()),
]

# Groups
group_settings: list[tuple[str, dict[str, Any]]] = [
    ("1", {"label": "1", "layout": layout_names["monadtall"]}),
    ("2", {"label": "2", "layout": layout_names["monadtall"]}),
    ("3", {"label": "3", "layout": layout_names["monadtall"]}),
    ("4", {"label": "4", "layout": layout_names["monadtall"]}),
    ("5", {"label": "5", "layout": layout_names["monadtall"]}),
    ("6", {"label": "6", "layout": layout_names["monadtall"]}),
]

groups: list[Any] = [Group(name, **kwargs) for name, kwargs in group_settings]

for i in groups:
    keys.extend(
        [
            Key([MOD], i.name, lazy.group[i.name].toscreen(toggle=True)),
            Key([MOD, "shift"], i.name, lazy.window.togroup(i.name)),
        ]
    )

# ScratchPads

scratchpad_conf: dict[str, Any] = {
    "warp_pointer": False,
    "height": 0.6,
    "y": 0.2,
    "opacity": 1,
}

groups.append(
    ScratchPad(
        "scratchpad",
        [
            DropDown("terminal", TERMINAL, **scratchpad_conf),
            DropDown(
                "newsboat",
                f"""{TERMINAL} newsboat -C=~/.config/newsboat/config 
                -u=~/sync/files/newsboat/urls -c=~/sync/files/newsboat/cache.db""",
                **scratchpad_conf,
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

# Screen and bar
screens = [Screen()]

# Misc
dgroups_key_binder = None
dgroups_app_rules = []  # type: list
follow_mouse_focus = True
bring_front_click = True
cursor_warp = False
reconfigure_screens = True
auto_fullscreen = True
auto_minimize = True
focus_on_window_activation = "urgent"
