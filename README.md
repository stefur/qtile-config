# Qtile configuration
This is my configuration for Qtile. A constant WIP. :)

## Key highlights in this config
- Volume widget that doesn't poll unless necessary (e.g. unless volume is increased/decreased/muted)
- Battery widget with battery level icons (using symbols from Nerd fonts)
- Spotify sets its wm_class late, meaning it's not catched by any rules when spawned. Using a hook to catch and push it to its assigned group (workspace).
- Window activation is set to urgent, with the exception of URLs. Again using a hook to focus Firefox when URLs are clicked.
- Spotify widget that uses DBus to pick up signals from Spotify to display playback status and information. Also allows for playback control via mouse callbacks.
- Discord is not minimizing properly on window kill. This means that a weird window artifact remains on screen. With a hook on window kill Discord is toggled to actually minmize to tray as it should.