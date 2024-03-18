# Changelog

## [5.1.1] 2024-03-18
### Fixed
- Hotfix for remote helper files not being fetched correctly

## [5.1.0] 2024-03-18
### Added
- Make columns in the server browser user-resizable (affects Server Browser, My Servers, and Recent Servers)
- Save dragged position of user-resized columns
- Display ping to server in statusbar: by popular request, added the ability to visualize both distance to server and round-trip latency (ping), at the cost of a small calculation delay. Please leave feedback regarding whether this feature feels fast/responsive enough.

### Fixed
- Fixed a rare scenario in Auto Mod Install Mode where defunct mods (mods no longer available on Steam) would try to be downloaded if the user had previously downloaded the mod

## [5.0.0] 2024-01-31
### Added
- Context switching: navigate to different pages using side buttons
- Dynamic statusbar: updates metadata and server distance when selecting rows
- Show server-side modlist and allow jumping to Steam Workshop pages to browse, and list whether mod is currently installed
- Print debug logs in-app (Help > Show debug log)
- Functionality to change API keys in-app (used when revoking old API keys)
- Print atomic mod sizes when listing installed mods
- Dialogs show direct links to API key management URLs when changing API keys
- Toggle dry-run mode directly from server browser
- Extensive keybindings for fully controlling the application without the mouse
- Extensive pre-boot sanity checks
- Keybinding help dialog in main menu
- Right-click context menus in server browsers/mod list: add/remove from favorites, show server-side mods, delete mod, copy server IP to clipboard

### Changed
- Utilize GTK bindings and MVC paradigm for UI creation and data flow
- Filter servers dynamically from within server browser
- Performance and security improvements to DZGUI helper files

### Fixed
- First-time setup dialogs respawning repeatedly in certain scenarios
- Issues with Steam client switching to the wrong page when using auto-mod install
- Set text input module correctly when launching on Steam Deck
- Separate current/total player count and use proper integer sort method in table

## [4.1.1] 2023-12-18
### Fixed

- News marquee not showing

## [4.1.0] 2023-12-17

This update adds support for DayZ servers running on a local area network. To connect or add to your server list, supply the server IP and query port in the format IP:PORT.

Support for Steam Deck Game Mode has also been restored, with a new dialog format that allows for virtual keyboard input. This should allow you to enter text in form fields by activating the Steam button + X. In addition, you can unlock the mouse and keyboard input when launching DZGUI through Steam by using an internal binding provided by Steam Deck: long-press the three dots button on the right of the device for three seconds to toggle the input state. This allows you to use mouse and keyboard-style bindings on Game Mode and vice versa.

### Added
- Virtual keyboard support for text entry fields on Steam Deck Game Mode
- Validate and connect to LAN server IPs

## [4.0.4] 2023-12-23
### Fixed
- Enforce version check for Python versions before 3.10

## [4.0.3] 2023-11-22
### Fixed
- Query helper: backwards compatibility for pre-2021 versions of Python 3

## [4.0.2] 2023-11-22
### Fixed
- Query helper not loading: fixed a remote link pointing to the wrong destination and added a checksum verification to ensure file is present

## [4.0.1] 2023-11-22
### Fixed
- Emergency hotfix to remove build artifacts leaking into main script: if you updated DZGUI from 3.3.18 to 4.0.0 between 2023-11-22 15:00:02 and 2023-11-22 15:03:37 GMT, there is a small chance it will be unable to launch correctly. If so, please follow the instructions on the manual to reinstall.

## [4.0.0] 2023-11-22

Hello players, this is a major version update which overhauls many of DZGUI's underlying systems to improve responsiveness of the application and make menus more intuitive to interact with. It should be considerably more difficult, if not impossible, to inadvertently crash a dialog, and nested dialogs should behave in a more expected fashion, such as when going back and forth between menus or changing options dynamically within a given menu.

In addition, with this update we are querying servers directly. The net benefit of this is that results will returned faster, bootup is faster, and it also paves the way for future features like connecting to servers on a LAN. The Battlemetrics API is now entirely optional and can be skipped during the setup process. However, if you have already set up a BM API key, you can continue using it if you want to query or add servers by ID instead of IP.

As part of this change, version 4.0.0 introduces the ability to connect to or add servers to your list based on either ID or IP. Previously, you could only connect by IP and add by IP, but now you can connect by IP/ID or add by IP/ID. If you choose the ID method, this will be translated into an IP seamlessly in the background. Similarly, favorite servers are now stored using the full IP rather than the ID. Due to the variety of systems and methods for connecting to servers, the application was carrying around and converting server IPs, IDs, and other formats back and forth, creating unnecessary complexity. By normalizing everything to an IP basis, maintainability should be more consistent. When upgrading to this version, your old favorites lists will be updated automatically to the new IP method. Note that as a result of this change, we must purge old history lists ("Recent Servers"), but everything else should carry over as before.

If you encounter any problems with this new release or with the migration of configs, please do not hesitate to submit a bug report.

Attention Fedora 38 users: problems with upstream GNOME packages causing crashes have been reported to GNOME development and a fix has been issued. You have the choice of compiling the zenity package 
from source or waiting until the latest version is merged into Fedora's package manager.

### Added
- Change in game name: dynamically change your profile name via the Advanced Options menu
- Connect by ID: supply a Battlemetrics ID to connect to a server; this can be used in lieu of the IP
- Add by IP: supply a standard IP to add a server to your list; this can be used as a more direct way of saving servers
- Filter by 1PP and 3PP in the server browser
- Save connected server to favorites: prior to connecting, asks the user if they want to save this server for future use
- Generate additional output when generating system logs

### Fixed
- Rare cases where the keyword filter would not filter server results correctly
- Handling of dialog exit signals: made it much more difficult to crash the application in rare cases when spamming input or returning from menus
- Update menus in place: when toggling options in the Advanced Options menu, displays the current state/mode of the option for better readability into what option is currently enabled
- More intuitive menu navigation: dialog setup and teardown is more responsive and follows expected flows when inside of nested menus
- Message formatting: fold long messages inside of popup dialogs for proper word wrapping regardless of screen type
- Fixed a rare case where dialogs would spawn twice during first-time setup
- Properly remain inside of menus when looping where it would make sense to do so : e.g., Delete Servers list, Advanced Options

### Changed
- Query servers directly to reduce API hops: initial bootup and subsequent server queries should be considerably faster
- Store complete IP:Port instead of server IDs
- Make Battlemetrics API key optional: this is only used for the 'Connect by ID' and 'Add server by ID' methods and is not required. If you prefer, you can simply connect/add by IP.
- Prevent the application from launching in Game Mode on Steam Deck: Steam Deck's kiosk mode has problems sending keyboard input to third party applications. To prevent unintended usage, DZGUI now warns the user to launch the app in Desktop Mode if they attempt to use it from Game Mode. Adding DZGUI as a Non-Steam Game does work on desktop PCs, but is not recommended due to the way Steam handles subshells. For best results, launch DZGUI directly via the script/applications menu (PC) or via the desktop icon (Steam Deck).
- Omit null servers from list: servers that time out or send an empty response are now omitted entirely from the My Servers list, as they will not return meaningful metadata unless they are online.  
  The My Servers list thus shows online and accessible servers

## [3.3.0] 2023-05-16
### Added
- Fetch more inclusive global "players in-game" count
- List mod directory on installed mods list
- Detect default Flatpak Steam path
- Dark mode/light mode theme to help file
- Alpha-sort My Servers list
- Add description of how to enable hidden folders on GTK2/3
- Initial logging framework

### Changed
- Test for wmctrl when enabling full auto mod installation
- Steam Deck: block toggling full auto mod installation due to extra dependencies needed
- First-time setup: sudo escalation when checking system map count for the first time

### Fixed
- Steam Deck: non-ASCII delimiter causing setup menu to despawn on some devices 
- Don't add items in My Servers multiple times to array when the list of favorites is paginated
- Trigger progress dialogs sooner and in sequence to reduce appearance of visual lag
- First-time setup: break out of dialogs correctly when user backs out
- First-time setup: break out of automatic path discovery when user specifies a path manually
- More portable interpreter invocation
- Properly size down window resolution when returning from server browser

## [3.2.10] 2023-05-11
### Fixed
- Return from lockfile function if first-time setup has not been run
- Sanitize inputs when using file picker
- Require both wmctrl and xdotool

## [3.2.9] 2023-05-10
### Changed
- Reword button to "Choose path manually" instead of "Retry"

## [3.2.7] 2023-05-10
### Changed
- Better sudo escalation within zenity dialogs if vm map count is too small

## [3.2.6] 2023-05-10
### Fixed
- Don't parse Flatpak symlinks when setting up default Steam path

## [3.2.5] 2023-05-07
### Fixed
- Require sudo when checking vm map count

## [3.2.4] 2023-03-01
### Fixed
- BM API returning stale query port and preventing fetching modlist

## [3.2.3] 2023-02-17
### Fixed
- sysctl map count value not being loaded immediately after setting
- Application terminating when user declines to update map count value
- Erroneous stderror output when flatpak is not installed

## [3.2.0] 2023-01-19
### Added
- Support Flatpak version of Steam

## [3.1.8] 2023-01-18
### Fixed
- Progress window blocking rest of window stack
- Bug when updating old mods if automod set to ON

## [3.1.7] 2023-01-06
### Fixed
- Hotfix for xdotool repeating input

## [3.1.6] 2023-01-01
### Changed
- Tick low pop servers by default

## [3.1.5] 2023-01-01
### Fixed
- Validate BM key on initial setup
- Fix history menu not parsing query ports correctly
### Changed
- More permissive Steam client discovery for tiling WMs

## [3.1.4] 2022-12-10
### Fixed
- Issue #43: Hotfix for workspace-driven WMs

## [3.1.3] 2022-12-06
### Fixed
- Explicitly require Python 3

## [3.1.1-2] 2022-12-03
### Fixed
- Fix lockfile path

## [3.1.0] 2022-12-03
### Added
- Recent connect history
- Simple, OS-agnostic automod installation
- Track local mod versions
- Force update local mods option
- Added python to dependencies
- File-picker driven path discovery on initial setup
### Dropped
- Headless mod installation
- Drop server ID field requirement on initial setup
### Changed
- Clean up main menu options
- Enforce Steam API key on initial setup
- More accurate path discovery on initial setup
- Add thousands separator to player counts in server browser
### Fixed
- Initial setup dialog causing early crash
- Improved error handling on initial setup to avoid malformed config files
- Delete server menu not clearing when returning to main menu
- Handle whitelist deletion when only one entry present
- Include path to drives under /run in path discovery
- Use Steam-safe local zenity version

## [3.0.7] 2022-11-25
### Fixed
- Hotfix for server reporting multiple versions of same mod

## [3.0.6] 2022-11-09
### Changed
- More verbose logs

## [3.0.5] 2022-10-27
### Fixed
- Properly create .desktop file on desktop PCs

## [3.0.3-4] 2022-10-16
### Fixed
- Steam Deck path discovery on first-time setup

## [3.0.2] 2022-10-12
### Fixed
- Size of certain popups on Steam Deck

## [3.0.1] 2022-10-12
### Fixed
- Initial popup size on Steam Deck

## [3.0.0] 2022-10-12
### Added
- Foreground progress of manual mod subscriptions
- Automatic mod helper through steamcmd
- Forum link
- Enforce Steam API
### Dropped
- Stop retrieving extra metadata from BM
### Changed
- Reorder main menu
- More verbose error messages
- Better abstraction of URLs
### Fixed
- Width and text of some popups on Steam Deck

## [2.7.2] 2022-10-07
### Fixed
- Fix internal URL

## [2.7.1] 2022-10-05
### Fixed
- Game launch not kicking off after symlink creation

## [2.7.0] 2022-10-04
### Added
- Server browser and geolocation algorithm
- More verbose error codes
- Additional progress bar setup and destruction throughout the application
- Additional API response validation
### Fixed
- Encapsulate title strings to prevent leaky arguments in title bars
- Remove erroneous slow boot process if first-time setup was already complete
- Delete server list not emptying when returning to main menu
### Changed
- Group main menu entries in advance of future functionality
- Better abstraction of paths
- Clarification of certain options and errors

## [2.6.3] 2022-10-02
### Fixed
- Hotfix for connect-to-fav not getting modlist

## [2.6.2] 2022-10-02
### Fixed
- Hotfix for BM API returning malformed publishedfileids

## [2.6.1] 2022-09-25
### Fixed
- Freedesktop shortcut errors

## [2.6.0] 2022-09-05
### Added
- Connect by IP method

## [2.5.1] 2022-08-17
### Fixed
- Hotfix for malformed paths during first-time setup

## [2.5.0] 2022-08-16
### Added
- Lockfile: prevent concurrent instances of DZGUI from being opened

### Changed
- Faster path discovery on first-time setup

### Fixed
- Symlink collision on servers with many mods
- API response pagination for large server lists

## [2.4.1] 2022-08-09
### Fixed
- Hotfix for progress bar breaking table when >9 servers in list

## [2.4.0] 2022-08-07
### Added
- Delete server command added to main menu
- Write log to file for bug reports
- Prompt to permanently increase map count size
- Dependency check for Steam
- Cover artwork
- News backend for OTA updates
- Clean up stale symlinks when checking mods

### Fixed
- Minify long mod launch params for servers with launch params breaking the upper limit
- Port DZTUI method of handling legacy symlinks
- Prevent user from entering invalid data on first-time setup
- Prompt to re-run first-time setup if config is malformed
- Better handling of field output from table
- Better Steam Deck detection and handling
- Prevent garbage in error messages
- Miscellaneous backend improvements

### Changed
- Enforce download when switching branches

## [2.3.2] 2022-08-04
### Fixed
Set branch flag to 'stable' if no config file present

## [2.3.1] 2022-08-04
### Fixed
- Improved error handling of first-time setup fields
- Interpolate config file values for debug, branch when writing file

### Changed
- Prompt user to restart first-time setup if broken config is found

## [2.3.0] 2022-07-18
### Added
- Numbered mod links in browser
- Admonition to upgrade versions for bug fixes
- Toggle branch between stable/testing

### Fixed
- Hotfix for fav server select on main menu

## [2.2.1] 2022-07-17
### Fixed
- Hotfix for upstream API returning malformed modlists
- Handle servers with no mods
- Fix dialog window depending on browser exit
- Remove stray newlines in config file

## [2.2.0] 2022-06-22
### Added
- Toggle debug mode in-app

## [2.1.0] 2022-06-19
### Changed
- Updated link to new documentation

## [2.0.3] 2022-06-17
### Fixed
- Safer expansion of originating script path

## [2.0.2] 2022-06-16
### Fixed
- Remove enforced runtime check of workshop path

## [2.0.2] 2022-06-16
### Fixed
- Expansion of Steam path prefix when default path was found

## [2.0.1] 2022-06-16
### Fixed
- Regenerate mod links file in browser when clicking dialog
- Reset whitelist when canceling one-shot (fav) mode

## [2.0.0] 2022-06-15
### Added
- Attempt to find DayZ path and write to config on first launch
- Merge existing config values into new config format when upgrading version
- Dynamically detect Steam Deck and set launch parameters
- Add "gametime" column to server list
- One-shot mode to open mod links in browser if using desktop
- Add favorite server from main menu
- Update favorite server changes in real time
- Add link to help pages from main menu
- Add link to changelog from main menu
### Changed
- Don't require duplication of fav server in whitelist
- More permissive truncation of long server names (50 char limit)
- Render mod list as a scrollable menu
- Reword errors for greater verbosity
- Initial support of granular error handling for API response codes
- Move extended path variables out of user config
### Fixed
- Check if mod dir is sane before listing mods
- Prevent favorite server launch if none set
- Reset server list to entire whitelist if canceling out of fav connect
- Do not load table on empty API response and warn user
- Suppress stderr cruft in logs and use logger instead

## [1.2.1] 2022-06-12
### Fixed
- Print the entire changelog
- Add confirmation dialog before run

## [1.2.0] 2022-06-12
### Changed
- Mod validation process now uses faster, single-pass API query
- Improved logger output when setting fav server

### Added
- In-app changelog

## [1.1.2] 2022-06-08
### Fixed
- Fix array used for mod concatenation; fetch post-sanitized list of mods

## [1.1.1] 2022-06-05
### Fixed
- Stricter regex to parse upstream version number

## [1.1.0] 2022-06-05
### Added
- Main menu: fav server label on header
- Main menu: add servers by ID directly into config file
- Main menu: link to report a bug
- Main menu: quick connect to fav server
- Connect: mod compatibility check
- Connect: mod download prompt
- Connect: mod auto symlinks
- New version download prompt
- Additional visualization of progress/menus
### Fixed
- Menu recursion when navigating backwards
### Changed
- Reduced ping timeout interval
