# Changelog

## [3.3.0] 2023-05-16

As of this version, to reduce verbosity, the Stable branch will only receive changelog updates for major and minor version increments, 
rather than for every hotfix. The Testing branch will continue to receive changelog updates for every hotfix under a release candidate.

## Fixed
## Added
## Changed

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
>>>>>>> c293fcd8c5136b6578f519b2f400d45bc01335cc

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
