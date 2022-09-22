# Changelog

## [Unreleased]
- Clean up logging
- Custom query API
- Standardize dialogs
- Query and connect by IP/port
 
 ## [2.7.0-rc.9] 2022-09-22
### Added
- Add alternative IP query method
 
## [2.7.0-rc.8] 2022-09-15
### Fixed
- Drop Python dependency

## [2.7.0-rc.7] 2022-09-14
### Added
- Verify IP table checksums when starting

### Changed
- Switch to C for helper logic

### Fixed
- Error handling for obscure servers returning no modlist

## [2.7.0-rc.6] 2022-09-13
### Added
- Add number of maps found to map select menu

### Fixed
- Strip Unicode spaces in server titles

## [2.7.0-rc.5] 2022-09-13
### Changed
- Improve server distance algorithm

### Fixed
- Strip Unicode spaces in server titles

## [2.7.0-rc.2 to 4] 2022-09-13
### Changed
- Retooling data in header

## [2.7.0-rc.1] 2022-09-12
### Added
- Initial server browser prototype

## [2.6.0-rc.5] 2022-09-03
### Fixed
- Make variable local

## [2.6.0-rc.4] 2022-09-03
### Fixed
- Use alternate API for direct IP queries

## [2.6.0-rc.3] 2022-09-03
### Changed
- Revert to legacy API method

## [2.6.0-rc.2] 2022-08-31
### Added
- Validate Steam API key

## [2.6.0-rc.1] 2022-08-16
### Added
- Connect to server by IP

## [2.5.0-rc.2] 2022-08-14
### Fixed
- Hotfix for server list responses with no next page cursor breaking table

## [2.5.0-rc.1] 2022-08-14
### Changed
- More performant path discovery, skip extraneous prompts

## [2.4.2-rc.5] 2022-08-13
### Fixed
- Cleaned typos and removed debug code

## [2.4.2-rc.4] 2022-08-13
### Fixed
- Clean up legacy symlinks

## [2.4.2-rc.3] 2022-08-13
### Fixed
- Alternate symlink method to prevent collisions in IDs

## [2.4.2-rc.2] 2022-08-10
### Fixed
- Pass correct query ports to modlist function

## [2.4.2-rc.1] 2022-08-10
### Fixed
- Page though API results to list >10 servers

## [2.4.1-testing] 2022-08-09
### Fixed
- Hotfix for progress bar breaking table when >9 servers in list

## [2.4.0-rc.10 - 2.4.0-rc.14] 2022-08-05
### Fixed
- Miscellaneous backend changes to test deployment of shortcuts to Steam Deck

## [2.4.0-rc.9] 2022-08-05
### Added
- Steam Deck artwork

## [2.4.0-rc.8] 2022-08-04
### Fixed
- Prevent word splitting of CPU result
- Correct path for writing .desktop files

## [2.4.0-rc.7] 2022-08-04
### Fixed
- Prevent user from entering invalid entries on first-time setup
- Prompt to re-run first-time setup if config is malformed
- Better handling of field output from table

### Added
- Prototype .desktop file for Steam Deck
- Generate bug report logs summarizing local settings

### Dropped
- Deprecated functions

## [2.4.0-rc.5] 2022-07-31
### Changed
- Drop download prompt for branch toggle

## [2.4.0-rc.4] 2022-07-31
### Fixed
- Source seen_news and debug values when writing new config file

## [2.4.0-rc.3] 2022-07-31
### Fixed
- Populate branch value correctly when staging config file

## [2.4.0-rc.2] 2022-07-31
### Fixed
- Enforce download when switching branches

## [2.4.0-rc.1] 2022-07-24
### Added
- Dependency check for Steam
- Delete server from list
- News backend for critical updates
- Prompt to permanently update sysctl map count
- Clean up stale symlinks if mods were deleted
- Backported DZTUI mod listing method (includes symlinks)
- Backported DZTUI method of encoding symlinks when handling large number of mods 
- Write dry-run launch options to file when in debug mode

### Fixed
- Prevent garbage in dependency check messages
- Send browser to background when opening links

### Changed
- Couple connect to fav and normal connect to same query function for maintainability
- Revert to old issues page index
- Hide header on unneeded pages
- Better detection of Steam Deck

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
