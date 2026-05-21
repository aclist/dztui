## Added
- Setup wizard
- Changelog text wrapping and formatting
- Changelog ships with source
- Documentation ships with source
- Decouple UI components into modules
- Choose from kilometer or miles distance display
- More granular haversine calculation
- Parse XDG data dirs with fallbacks
- Dedicated mods page
- Dedicated thanks page
- Rearrange menus/breadcrumbs
- Open filepicker when generating system log
- Developers page (and -d flag)
- Redact API key in log table
- Integrate add/connect widgets into main menu
- Favorite/connect/LAN panels integrated with server views
- Abort on first LAN server found
- Colorized IP/ID validation fields
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
- Add server name to server mod dialogs
- Lazy load ping cell data func
- Refresh servers button
- Early load alerts button
- Preconnect dialog
- Preconnect warnings/failsafes like filesize
- Save filters per server context between sessions


## Changed
- Conform to PEP 440 versioning for beta versions
- Reduce padding on keys button
- Boldface breadcrumbs
- Bold labels inside frames
- Sidebar buttons do not steal focus
- Copy IP copies IP:queryport only instead of IP:gameport:queryport, mimics syntax needed by add by ip method
- Load new model into view without flushing
- Cull servers with abnormal queue values (integer overflow: 2147483647)
- Packaging structure
- Suppress log messages from imported modules
- Embed Workshop link in Options menu
- Disable overlay scrollbars on server tables

## Dropped
- Debug mode
- Branch switching
- Manual mod install mode (describe rationale)
- Force update mods

## Fixed
- Longstanding issue with left clicks not registering as tree selection changes after spamming keyboard input
- Center server title text on server dialogs
- Rare segfaults when changing maps (threading)
- Moved dialogs out of threads

## Unreleased
- Load offline mods
- Choose to jump into splash screen instead of server
- Local documentation
- Raw debug command in context menu

## Developer-facing
- Add pyproject.toml file
- Show deprecation warnings
- Options -> Dev page
