## What this is
DZGUI is a turnkey browser and mod manager for DayZ on Linux. It allows you to connect to both official and modded/community DayZ servers on Linux via a graphical user interface (GUI).

This overcomes certain limitations in the Linux client and helps prepare the game to launch by providing features like:

- Search for and display global and LAN servers via an interactive table
- Supports official, third-party, and modded DayZ servers
- Automatically find and prepare mods being requested by servers
- Add/delete/manage favorite servers by IP or ID
- Quick-connect to favorite/recent servers
- Manage local mods and symlinks
- Prepare launch options to pass to Steam

## Setup and usage

Please refer to the documentation for installation and setup instructions:

- [GitHub](https://aclist.github.io/dzgui/index.html)
- [Codeberg (Mirror)](https://aclist.codeberg.page)

![A screenshot of DZGUI](/images/example.png)

## Attribution

Geolocation records from [DB-IP](https://db-ip.com) under [CC 4.0 license](https://creativecommons.org/licenses/by/4.0/)

This tool uses [python-a2s](https://github.com/Yepoleb/python-a2s) and [dayzquery](https://github.com/Yepoleb/dayzquery) as submodules; licenses for these submodules can be found in the LICENSES file
of the project root.

Both the geolocation records and submodules listed above are not shipped with the source code, but are retrieved and assembled at runtime.

Finally, executable versions of DZGUI shipped as release binaries are thin wrappers around the Python interpreter, and also retrieve and assemble the above dependencies at runtime on the end-user's
machine, rather than using pre-compiled source code. Users wishing to review these dependencies can inspect the 'pyproject.toml' manifest in the project root.

## Disclaimer

DZGUI is beta-quality software and is provided as-is.
