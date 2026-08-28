from dataclasses import dataclass
from dzgui.const.constants import SYSTEM_LOG


# General
dialog_header = "DZGUI - Dialog"
dz = "DayZ"
dz_exp = "DayZ Experimental"
delimiter = "␞"

# GenericDialog
main_menu = "Return to main menu"
exit_app = "Exit"
server_details = "Server details"
modlist = "Modlist"
input_required = "User input required"
confirm = "Confirmation"
notice = "Notice"
wait = "Please wait"
restart_required = "App relaunch required"

# Wait dialogs
ping = "Ping"
mod = "Mod"
_id = "ID"

# ContextMenu
add_note = "Add note"
edit_note = "Edit note"
show_mods = "Show server-side mods"
show_details = "Show server details"
refresh_players = "Refresh player count"
open_workshop = "Open in Steam Workshop"
unsub_mod = "Unsubscribe mod"
copy_name = "Copy name to clipboard"
copy_ip = "Copy IP to clipboard"
copy_log = "Copy record(s) to clipboard"
add = "Add to Saved Servers"
add_fav = "Set as favorite"
remove = "Remove from Saved Servers"
remove_history = "Remove from history"
connect = "Connect"

# Columns
server_mod_cols = ["Mod", "ID", "Installed"]
mod_cols = ["Mod", "Symlink", "ID", "Size (MiB)", "Color"]
log_cols = ["Timestamp", "Flag", "Traceback", "Message"]
browser_cols = [
    "Name",
    "Map",
    "View",
    "Gametime",
    "Players",
    "Max",
    "Queue",
    "IP",
    "Qport",
    "Ping",
]

# DetailsDialog
server_message = "Server message"
workshop = "Enter/double click a row to open in Steam Workshop."

# LanDialog
default_port = "Use default query port (27016)"
custom_port = "Enter custom query port"
scan_servers = "Scan LAN servers"
select_port = "Select the query port"

# Errors
error_heading = "Error"
config_not_found = "DZGUI configuration file not found. Please exit and restart."
cannot_acquire_lock = "DZGUI is already open."
something_wrong = "Something went wrong. See the detailed error below."
steam_key_missing = "No Steam API key is set."
malformed_mods = "Found mods on system, but was unable to parse results."
steam_missing = "Local Steam installation is not set, possibly malformed config file."
build_corrupted = (
    "Steam settings or DayZ installation may be corrupted. Try restarting Steam."
)
server_timeout = "Timed out when querying server(s). Check IP or try again later."
server_error = (
    "Error while contacting server, possibly timed out. Please wait and try again."
)
server_protected = (
    "This server is password-protected and you will be "
    "prompted when connecting. Do you want to proceed?"
)


# KeybindingsDialog
navigation = {
    "Enter/space/double click": "select row item",
    "Down arrow": "move down a row/scroll down",
    "Up arrow": "move up a row/scroll up",
    "Right arrow": "jump to sidebar from main area",
    "Left arrow": "jump to main area from sidebar",
    "Tab": "cycle forward through elements",
    "Shift-tab": "cycle backward through elements",
    "ESC/Enter": "close dialogs",
    "?": "show/hide this dialog",
    "Ctrl-q": "Quit",
}
servers = {
    "Enter/space/double-click": "connect to server",
    "Right-click/Ctrl-l": "additional context menus",
    "Ctrl-r": "refresh players",
    "Ctrl-f": "jump to keyword search field",
    "Ctrl-m": "jump to maps field",
    "Ctrl-d": "select default LAN port",
    "Ctrl-n": "select custom LAN port",
    "Ctrl-u": "connect to server from preconnect dialog",
    "Ctrl-i": "jump to IP insert field",
    "n": "navigate to next tab",
    "p": "navigate to previous tab",
    "ESC": "return to table",
    "1-9": "toggle filter 1-9 on/off",
    "0": "toggle filter 10",
    "Minus": "toggle filter 11",
    "Backslash": "toggle filter 12",
}
vim = {
    "j": "Move down a row/scroll up",
    "k": "Move up a row/scroll down",
    "h": "Jump to main area from sidebar",
    "l": "Jump to sidebar from main area",
    "g": "Jump to first row/top of page",
    "G": "Jump to last row/bottom of page",
}
key_contexts = ["Servers", "Navigation", "Vim-style keys"]
key_header = "Keybindings"

# ModSelectionPanel

# labels
label_main_menu = "Main menu"

# buttons
ping_servers = "Ping servers"
ping_tooltip = (
    "Refresh the ping for visible servers.\n" "Available once per unique filter context"
)

# statusbar_helptext = "Select a row to see its detailed description"
# statusbar_helptext = "No server metadata to list."

# use e.g. filters.1pp
filter_1pp = "1PP"
filter_3pp = "3PP"
filter_day = "Day"
filter_night = "Night"
filter_empty = "Empty"
filter_full = "Full"
filter_lowpop = "Low pop"
filter_nonascii = "Non-ASCII"
filter_duplicate = "Duplicate"
filter_official = "Official"
filter_unofficial = "Unofficial"
filter_modded = "Modded"

# maps
all_maps = "All maps"

# state
unknown = "Unknown"
none_provided = "None provided"
disabled = "Disabled"
enabled = "Enabled"
null = "-"
unspecified = "not specified"

# DLC
dlc_frostline = "Frostline"
dlc_badlands = "Badlands"
dlc_none = "None"

# platform
windows = "Windows"
linux = "Linux"

# misc
self_workshop = "Open Steam workshop"
settings_updated = "Settings updated!"


@dataclass(slots=True, frozen=True)
class ModPanelStrings:
    header: str
    unhighlight_stale: str
    unhighlight_stale_tooltip: str
    highlight_stale: str
    highlight_stale_tooltip: str
    unsub_selected: str
    unsub_selected_tooltip: str
    unselect_all: str
    unselect_all_tooltip: str
    select_all: str
    select_all_tooltip: str
    bulk_select: str
    clear_highlights: str
    select_stale: str
    select_stale_tooltip: str


@dataclass(slots=True, frozen=True)
class Dialog:
    querying: str
    fetching: str
    filtering: str
    refreshing: str
    details: str
    modlist: str
    working: str
    updating_mods: str
    scanning: str


@dataclass(slots=True, frozen=True)
class Init:
    is_steam_running: str
    is_dayz_running: str
    requires_steam: str


@dataclass(slots=True, frozen=True)
class Button:
    servers_label: str
    servers_tooltip: str
    mods_label: str
    mods_tooltip: str
    options_label: str
    options_tooltip: str
    help_label: str
    help_tooltip: str
    exit_label: str
    exit_tooltip: str


@dataclass(slots=True, frozen=True)
class Crumbs:
    changelog: str
    keys: str
    log: str
    _help: str
    mods: str
    options: str
    servers: str
    thanks: str
    developers: str
    default: str
    offline: str


@dataclass(slots=True, frozen=True)
class Thanks:
    header: str
    description: str
    users: list[str]


@dataclass(slots=True, frozen=True)
class Options:
    header: str
    steam_web: str
    enter_steam: str
    steam_placeholder: str
    name_placeholder: str
    last_used: str
    always_fs: str
    steam: str
    flatpak: str
    km: str
    mi: str
    client: str
    window_size: str
    distance: str
    name: str
    manual_dl: str
    auto_dl: str
    update: str
    install_mode: str
    force_update: str
    dl_eventbox: str
    force_eventbox: str
    self_update: str
    no_self_update: str
    api_key: str
    prefs: str
    mods: str
    version: str
    branch: str
    stable: str
    testing: str
    manual_sub_msg: str


init = Init(
    is_steam_running="Is Steam running? DZGUI must be run on top of Steam.",
    is_dayz_running="Is DayZ already running? DZGUI cannot launch DayZ if another process is using it.",
    requires_steam="DZGUI requires that Steam or Flatpak Steam be installed on the system.",
)

mod_panel = ModPanelStrings(
    header="Mod actions",
    unhighlight_stale="Unhighlight stale",
    unhighlight_stale_tooltip="Clears highlight from stale mods",
    highlight_stale="Highlight stale",
    highlight_stale_tooltip=(
        "Shows locally-installed mods which are not \n"
        "used by any server in your Saved Servers"
    ),
    unsub_selected="Unsubscribe selected",
    unsub_selected_tooltip="Unsubscribes from selected mods",
    unselect_all="Unselect all",
    unselect_all_tooltip="Bulk unselects all mods",
    select_all="Select all",
    select_all_tooltip="Bulk selects all mods",
    bulk_select="Bulk selects all currently highlighted mods",
    clear_highlights="Clears highlights and reverts the table to a default state",
    select_stale="Select stale",
    select_stale_tooltip="Only selects highlighted stale mods",
)


thanks = Thanks(
    header="# Special thanks",
    description=(
        "This page recognizes beta testers, collaborators, code "
        "contributors, and sponsors of the project in alphabetical order.\n"
        "If you wish to be removed from this list, please submit a ticket."
    ),
    users=[
        "bongjutsu",
        "Deku",
        "dj3hac",
        "finntux",
        "GaryBlackbourne",
        "jiriks74",
        "Johnofwrong",
        "MatheusLasserr",
        "nolan-perez",
        "OnniSaarni",
        "scandalouss",
        "SnackSBR",
        "StevelDusa",
        "Thoughtduck216",
    ],
)


options = Options(
    header="Options",
    steam_web="Steam API page",
    enter_steam="Enter your Steam API key",
    steam_placeholder="Steam API key",
    name_placeholder="Identifies you to other players in-game",
    last_used="Last used dimensions",
    always_fs="Always fullscreen",
    steam="Steam",
    flatpak="Flatpak (experimental)",
    km="km (kilometers)",
    mi="mi (miles)",
    client="Steam client",
    window_size="Window size at boot",
    distance="Distance display",
    name="Player name",
    manual_dl="Manual",
    auto_dl="Auto",
    update="Update",
    install_mode="Mod install mode",
    force_update="Force update local mods",
    dl_eventbox=(
        "Manual: prompt to subscribe to mods in Steam. " "Auto: unmanned downloads."
    ),
    force_eventbox="Synchronize all local mods. Automatic mode must be enabled.",
    self_update=(
        "Stable: only contains stable features. "
        "Testing: pre-release beta, contains new features."
    ),
    no_self_update=(
        "In-app updates are disabled when DZGUI is "
        "installed globally (e.g., via package manager)."
    ),
    api_key="API Key",
    prefs="Preferences",
    mods="Mods",
    version="Version",
    branch="DZGUI branch",
    stable="Stable",
    testing="Testing",
    manual_sub_msg="""When switching from MANUAL to AUTO mod install mode,
DZGUI will manage mod installation and deletion for you.
To prevent conflicts with Steam Workshop subscriptions and old mods from being downloaded
when Steam updates, you should unsubscribe from any existing Workshop mods you manually subscribed to.
Open your Profile, then 'Workshop Items' and select 'Unsubscribe from all'
on the right-hand side.
""",
)

dialog = Dialog(
    querying="Querying server",
    fetching="Fetching server metadata",
    filtering="Filtering servers",
    refreshing="Refreshing player count",
    details="Fetching details",
    modlist="Fetching modlist",
    working="Working",
    updating_mods="Updating mods",
    scanning="Scanning LAN ports",
)

buttons = Button(
    servers_label="Servers",
    servers_tooltip="Search for and connect to servers",
    mods_label="Mods",
    mods_tooltip="Manage local mods",
    options_label="Options",
    options_tooltip="Advanced options",
    help_label="Help",
    help_tooltip="Troubleshooting and documentation",
    exit_label="Exit",
    exit_tooltip="Quits the application",
)

crumbs = Crumbs(
    changelog="Help > Changelog",
    keys="Keybindings",
    log="Help > Debug log",
    _help="Help",
    mods="Mods",
    options="Options",
    servers="Servers > Server browser",
    thanks="Help > Special thanks",
    developers="Options > Developers",
    default="Servers > ",
    offline="Mods > Play offline",
)

no_mods = "No local mods found."
no_servers = "No server metadata to list."


@dataclass(slots=True, frozen=True)
class Flags:
    description: str
    version: str
    uninstall: str
    debug: str
    map_count: str


flags = Flags(
    description="DayZ server browser and mod manager",
    version="print version information",
    uninstall="clean up state/config files",
    debug="enable developer debugging features",
    map_count="check and update system map count value",
)


@dataclass(slots=True, frozen=True)
class FilePicker:
    title: str
    placeholder: str


picker = FilePicker(
    title="Save diagnostic log to file",
    placeholder=SYSTEM_LOG,
)

api_error = (
    "API key validation error or timeout. See 'Help > Show debug log' for details."
)


@dataclass(slots=True, frozen=True)
class DevelopersPage:
    header: str
    paths_label: str
    prefs_label: str
    columns: list[str]


developers = DevelopersPage(
    header="Developers",
    paths_label="Resolved XDG paths",
    prefs_label="Boot preferences",
    columns=["Key", "Value"],
)


@dataclass(slots=True, frozen=True)
class ServerLabels:
    browser: str
    saved: str
    recent: str
    lan: str


server_labels = ServerLabels(
    browser="Server Browser",
    saved="Saved Servers",
    recent="Recent",
    lan="LAN",
)


distance_suffix = "Distance: calculating..."
dialog_error = "ERROR"


@dataclass(slots=True, frozen=True)
class AtomicButton:
    refresh: str
    refresh_tooltip: str
    copy: str
    keys: str
    keys_tooltip: str


atomic_buttons = AtomicButton(
    refresh="Refresh",
    refresh_tooltip="Refresh server data",
    copy="Copy",
    keys="Keys",
    keys_tooltip="Toggles the keybindings dialog",
)

gtk_theme_missing = "No GTK theme provided"
steam_icon_missing = "Steam icon not found in IconTheme"

missing_changelog = "Error: failed to read changelog"
esc_to_return = "Press ESC to return"
question_to_return = "Press ? to return"

alert_button_tooltip = "Click to open debug log"

address_already_saved = "This address is already in your Saved Servers"
stop_scanning = "Stop scanning on first hit"
abort_tooltip = "Unless you have multiple DayZ servers on your LAN,\nleave this checked to get results faster"
