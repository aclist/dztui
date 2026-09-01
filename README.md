## What this is
DZGUI is a turnkey server browser and mod manager for DayZ on Linux. It allows you to connect to both official and modded/community DayZ servers on Linux via a graphical user interface (GUI).

This overcomes certain limitations in the Linux client and helps prepare the game to launch by providing features like:

- Search for and display global and LAN servers via an interactive table
- Supports official, third-party, and modded DayZ servers
- Automatically find and prepare mods being requested by servers
- Quick-connect to favorite/recent servers
- Manage and delete local mods
- And more

## Design philosophy

DZGUI follows a specific set of guidelines, enumerated below:

- Provide a free and open-source tool under GPL
- Do not use undocumented, third-party servers to aggregate data; no central "DZGUI" server
- All connections go to Steam and DayZ servers directly; the tool should function in perpetuity without intermediary endpoints
- Target Linux desktop and Steam deck specifically; not a cross-platform tool

## Setup and usage

Please refer to the documentation for installation and setup instructions:

- [GitHub](https://aclist.github.io/dzgui/index.html)
- [Codeberg (Mirror)](https://aclist.codeberg.page)

![A screenshot of DZGUI](/dzgui/data/images/example.png)

## Attribution

Geolocation records from [DB-IP](https://db-ip.com) under [CC 4.0 license](https://creativecommons.org/licenses/by/4.0/)

Executable versions of DZGUI published as release binaries ship with various runtime dependencies and the Python interpreter built in.
Users wishing to review the licenses to these components can inspect the `LICENSE` file located in the release tarball.

## Disclaimer

DZGUI is beta-quality software and is provided as-is.
