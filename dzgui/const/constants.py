APPID_DAYZ = 221100
APPID_DAYZ_EXP = 1024020
UDP_PORT = 27016
VM_FILE = "/proc/sys/vm/max_map_count"
MIN_COUNT = 1048576

REQUEST_TIMEOUT = 10

APPNAME_DAYZ = "DayZ"
APPNAME_DAYZ_EXP = "DayZ Exp"
APPNAME_DAYZ_EXP_HUMAN = "DayZ Experimental"
DAYZ_BINARY = "DayZ_x64.exe"

LIBRARYFOLDERS_PATH = "steamapps/libraryfolders.vdf"
WORKSHOP_PATH = "steamapps/workshop/content/" + str(APPID_DAYZ)

STEAM_CMD = "steam"
FLATPAK_CMD = "flatpak"
FLATPAK_APPID = "com.valvesoftware.Steam"
FLATPAK_RUN_CMD = "flatpak run " + FLATPAK_APPID
FLATPAK_SANDBOX = "flatpak-spawn --host flatpak run " + FLATPAK_APPID

AUTHOR = "aclist"
STABLE_REPO = "stable"
BETA_REPO = "testing"

APP_NAME = "DZGUI"
APP_NAME_LOWER = "dzgui"
APP_NAME_ABBR = "dzg"

HEX_GREEN = "#32CD32"
HEX_RED = "#FF0000"
HEX_ORANGE = "#FFAC1C"

CARET_DOWN = "go-down-symbolic"
CARET_UP = "go-up-symbolic"
CLIPBOARD = "edit-copy-symbolic"
FOLDER = "folder-symbolic"
ERROR = "dialog-error-symbolic"
HELP_BUBBLE = "help-about-symbolic"
INPUT_KEYBOARD = "input-keyboard-symbolic"
LIST_ADD = "list-add-symbolic"
REFRESH_ICON = "view-refresh-symbolic"
SEARCH_ICON = "system-search-symbolic"
STEAM_ICON = "steam_tray_mono"
VIEW_CONCEAL = "view-conceal-symbolic"
VIEW_REVEAL = "view-reveal-symbolic"
WARNING = "dialog-warning-symbolic"
WEB_BROWSER = "web-browser-symbolic"

SEPARATOR = "SEPARATOR"

# TODO: drop
NO_PADDING = 0
NO_EXPAND = False
NO_FILL = False
EXPAND = True
FILL = True

SCROLL_INCREMENT = 50
WINDOW_DEFAULT_X = 1400
WINDOW_DEFAULT_Y = 800

LEGACY_CONFIG_PATH = ".config/dztui/dztuirc"
LEGACY_COLS_PATH = ".local/state/dzgui/dzg.cols.json"
LEGACY_IPS_PATH = ".local/share/dzgui/helpers/ips.csv"

DEBUG_LOG = f"{APP_NAME}_DEBUG.LOG"
SYSTEM_LOG = f"{APP_NAME}_SYSTEM.LOG"
CHANGELOG_PATH = "data/CHANGELOG.md"
HERO_PATH = "data/images/hero.png"
CSS_PATH = "data/app.css"
VDF_PATH = "steamapps/libraryfolders.vdf"
DEFAULT_STEAM_PATH = ".local/share/Steam"
FLATPAK_STEAM_PATH = ".var/app/com.valvesoftware.Steam/data/Steam"
UBUNTU_STEAM_PATH = ".steam/steam"
DEBIAN_STEAM_PATH = ".steam/debian-installation"

LOG_FILTERS = ("CRITICAL", "WARNING", "INFO", "DEBUG")

TMP_PATH = "/tmp"
TMP_TARBALL = "/tmp/dzgui.tar.gz"
TMP_EXE = "/tmp/dzgui/dzgui"
