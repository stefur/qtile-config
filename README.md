## Qtile configuration
This is my configuration for [Qtile](https://github.com/qtile/qtile). It's geared towards Qtile `HEAD` and a constant WIP. :)

![](screenshot.png)
*Screenshot as of `0ffe24d`.*

### Highlights
Some functionality here may be of interest to others, so I've tried to summarize them here.

**Spawn or focus**  
Also sometimes known as "*run or raise*" in other tiling window managers, such as Xmonad. The basic idea is to check if an application is already running before it's spawned. If it's running, focus the window.

The by far easiest solution is to use an application like `wmctrl` in a script, but I decided to implement something that wouldn't depend on any 3rd party application.

The command to run an app does not always correspond to the `wm_class`. For example running `steam-native`gives the class string `steam`.

To mitigate this I set up the following dict:

```
appcmd_to_wm_class = {
    'signal-desktop': 'signal',
    'steam-native': 'Steam'
}
```

The method to spawn or focus is the following:

```
@lazy.function
def spawn_or_focus(qtile, app):
    try:

        # Check if the app is in the dict first, otherwise just use the app as wm_class
        app_wm_class = appcmd_to_wm_class.get(app) if app in appcmd_to_wm_class else app
        
        # Get the windows of all open windows
        windows = set(qtile.windows_map[wid].window for wid in qtile.windows_map)

        # Select the window with a matching WM class and find its group
        window = [window for window in windows if app_wm_class in window.get_wm_class()][0]
        win_on_group = str(window.get_wm_desktop() + 1)
        group = qtile.groups_map[win_on_group]

        # Go to the group and set input forcus to the window
        qtile.current_screen.set_group(group)
        window.set_input_focus()

    except IndexError:
        qtile.cmd_spawn(app)
```

In the keybinds the above method can be used as:
```
EzKey('M-c', spawn_or_focus('signal-desktop'))
```

*Below will be expanded later on*

**Only allow focus browser if a URL is clicked, other windows are set to urgent**  
Window activation is set to urgent in the config. This means that no windows take focus on window activation.
However I want to focus the browser if its flagged as urgent, e.g. when clicking a URL. This is achieved using a hook.

**Spotify group assign workaround**  
Spotify sets its wm_class late, meaning it's not catched by any rules when spawned. Instead I use a hook to catch and push it to its assigned group (workspace).

**Simple layout toggle**  
Toggle layout by name rather than index.

**Volume widget that doesn't poll unless necessary**
E.g. unless volume is increased/decreased/muted.

**Battery widget with battery level icons**  
Using symbols from Nerd Fonts.

**Spotify widget**  
Spotify widget that uses DBus to pick up signals from Spotify to display playback status and information. Also allows for playback control via mouse callbacks.

**Discord fix**
Discord is not minimizing properly on window kill. This is an issue specific for my laptop and I have no idea why. The issues results in a weird window artifact remaining on screen every time. With a hook on window kill Discord is toggled to actually minimize to tray as it should.