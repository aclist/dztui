## Added
- Add pyproject.toml file
- Changelog text wrapping and formatting
- Decouple UI components into modules
- Choose from kilometer or miles distance display
- More granular haversine calculation
- Parse XDG data dirs with fallbacks
- Dedicated mods page
- Dedicated thanks page
- Rearrange menus/breadcrumbs
- Documentation ships with source
- Open filepicker when generating system log
- Developers page (and -d flag)
- Redact API key in log table
- Integrate add/connect widgets into main menu
- Favorite/connect/LAN panels integrated with server views
- Colorized IP/ID validation
- Copy favorite server IP to clipboard
- Set favorite server from tables
- Detailed/copyable trace in critical error dialogs
- Visual icons
- Integrated server notebook
- Propagate width changes to all tables
- Remember tree position in menus
- Show hidden server count after filtering
- Atomic map filters per server context
- Use concurrency when checking stale mods (performance uplift)
- Copy version by clicking label

## Changed
- Reduce padding on keys button
- Boldface breadcrumbs
- Bold labels inside frames
- Sidebar buttos do not steal focus
- Copy IP copies IP:queryport only instead of IP:gameport:queryport, mimics syntax needed by add by ip method
- Load new model into view without flushing

## Fixed
- Longstanding issue with left clicks not registering as tree selection changes after spamming keyboard input
- Rare segfaults when changing maps (threading)
- Moved dialogs out of threads

## Unreleased
- Load offline mods
- Choose to jump into splash screen instead of server
- Setup wizard
- Move debug mode to developers only
- Local documentation

## Devs
- Show deprecation warnings
- Options -> Dev page
- Raw debug command
- Moved debug log to this mode
