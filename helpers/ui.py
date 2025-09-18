import csv
import json
import locale
import logging
import multiprocessing
import os
import re
import signal
import subprocess
import sys
import textwrap
import threading
import typing  # noqa
import warnings

from dataclasses import dataclass
from enum import Enum
from collections.abc import Callable
from concurrent.futures import wait
from concurrent.futures import ThreadPoolExecutor
from typing import Literal, Self, Any

import servers as Servers  # noqa E402
import pefile as PeFile  # noqa E402

from pefile import (
    VDFLoadError,
    AppNotInstalledError,
    AppMovedError,
    PeFileError,
)
from pefile import VersionMatch

locale.setlocale(locale.LC_ALL, "")

import gi  # noqa E402

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402

# https://bugzilla.gnome.org/show_bug.cgi?id=708676
warnings.filterwarnings("ignore", ".*g_value_get_int", Warning)

app_name = "DZGUI"
app_name_lower = app_name.lower()
app_name_abbr = "dzg"
delimiter = "␞"

APPID_DAYZ = 221100
APPID_DAYZ_EXP = 1024020

cache: dict[str, int] = {}
config_vals: list[str] = []

_VERSION: str
IS_GAME_MODE: bool
IS_STEAM_DECK: bool

map_store = Gtk.ListStore(str)
row_store = Gtk.ListStore(str)
modlist_store = Gtk.ListStore(str, str, str)
mod_store = Gtk.ListStore(str, str, str, float, str)
log_store = Gtk.ListStore(str, str, str, str)

user_path = os.path.expanduser("~")
cache_path = f"{user_path}/.cache/{app_name_lower}"
state_path = f"{user_path}/.local/state/{app_name_lower}"
helpers_path = f"{user_path}/.local/share/{app_name_lower}/helpers"
log_path = f"{state_path}/logs"
changelog_path = f"{state_path}/CHANGELOG.md"
geometry_path = f"{state_path}/{app_name_abbr}.cols.json"
res_path = f"{state_path}/{app_name_abbr}.res.json"
funcs = f"{helpers_path}/funcs"
mods_temp_file = f"{cache_path}/{app_name_abbr}.mods_temp"
stale_mods_temp_file = f"{cache_path}/{app_name_abbr}.stale_mods_temp"
servers_path = f"{cache_path}/{app_name_abbr}.servers"
config_path = f"{user_path}/.config/dztui"
config_file = f"{config_path}/dztuirc"
history_file = f"{state_path}/{app_name_abbr}.history"

logger = logging.getLogger(__name__)
log_file = f"{log_path}/{app_name}_DEBUG.log"
system_log = f"{log_path}/{app_name}_SYSTEM.log"
FORMAT = "%(asctime)s␞%(levelname)s␞%(filename)s::%(funcName)s::%(lineno)s␞%(message)s"
logging.basicConfig(filename=log_file, format=FORMAT, level=logging.DEBUG)

manual_sub_msg = """When switching from MANUAL to AUTO mod install mode,
DZGUI will manage mod installation and deletion for you.
To prevent conflicts with Steam Workshop subscriptions and old mods from being downloaded
when Steam updates, you should unsubscribe from any existing Workshop mods you manually subscribed to.
Open your Profile > Workshop Items and select 'Unsubscribe from all'
on the right-hand side, then click OK below to enable AUTO mod install mode.
"""

api_warn_msg = """No servers returned. Possible causes:
no servers in favorites/history, local network issue, or API key on cooldown.
Return to the main menu, wait 30s, and try again.
If this issue persists, your API key may be defunct.
"""


@dataclass(slots=True)
class Record:
    ip: str
    gameport: int
    qport: int


class Preferences(Enum):
    STEAM = 1
    BM = 2
    WINDOW = 3
    CLIENT = 4
    NAME = 5
    INSTALL = 6


class Port(Enum):
    DEFAULT = 1
    CUSTOM = 2


class Popup(Enum):
    WAIT = 1
    NOTIFY = 2
    CONFIRM = 3
    ENTRY = 4
    RETURN = 5
    MODLIST = 6
    DETAILS = 7
    QUIT = 8


class NotebookPage(Enum):
    # enums correspond to the page in linear order
    MAIN = 0
    CHANGELOG = 1
    KEYS = 2
    OPTIONS = 3


class Command(Enum):
    INTERACTIVE = 1
    ONESHOT = 2
    HELP = 3
    TOGGLE = 4


class VAdjustment(Enum):
    UP = 1
    DOWN = 2
    TOP = 3
    BOTTOM = 4


class CursorPosition(Enum):
    UP = 1
    DOWN = 2
    TOP = 3
    BOTTOM = 4


class FilterMode(Enum):
    KEYWORD = 1
    MAP = 2
    INITIAL = 3
    TOGGLE_OFF = 4
    TOGGLE_ON = 5


class EnumWithAttrs(Enum):
    def __new__(cls, *args, **kwargs) -> Self:
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, d: dict):
        self.dict = d


class RowType(EnumWithAttrs):
    @classmethod
    def str2rowtype(cls, string: str) -> "RowType":
        for member in cls:
            if string == member.dict["label"]:
                return member
        return RowType.DYNAMIC

    # specialized behavior
    DYNAMIC = {
        "label": None,
        "tooltip": None,
    }
    RESOLVE_IP = {
        "label": "Resolve IP",
        "tooltip": None,
        "wait_msg": "Resolving remote IP",
    }
    HIGHLIGHT = {
        "label": "Highlight stale",
        "tooltip": None,
        "wait_msg": "Looking for stale mods",
    }

    # pages
    SERVER_BROWSER = {
        "label": "Server browser",
        "tooltip": "Used to browse the global server list",
        "type": "server",
    }
    SAVED_SERVERS = {
        "label": "My saved servers",
        "tooltip": "Browse your saved servers. Unreachable servers will be excluded",
        "type": "server",
    }
    RECENT_SERVERS = {
        "label": "Recent servers",
        "tooltip": "Shows the last 10 servers you connected to (includes attempts)",
        "type": "server",
    }
    SCAN_LAN = {
        "label": "Scan LAN servers",
        "tooltip": "Search for servers on your local network",
        "type": "server",
    }
    LIST_MODS = {
        "label": "List installed mods",
        "tooltip": "Browse a list of locally-installed mods",
        "quad_label": "Mods",
        "type": "mods",
    }
    CHANGELOG = {
        "label": "View changelog",
        "tooltip": "Opens the DZGUI changelog in a dialog window",
    }
    OPTIONS = {"label": "Options", "tooltip": None}
    KEYBINDINGS = {"label": "Keybindings", "tooltip": None}
    SHOW_LOG = {
        "label": "Show debug log",
        "tooltip": "Read the DZGUI log generated since startup",
        "quad_label": "Debug log",
    }

    # interactive dialogs
    CONN_BY_IP = {
        "label": "Connect by IP",
        "tooltip": "Connect to a server by IP",
        "prompt": "Enter IP in IP:Queryport format (e.g. 192.168.1.1:27016)",
        "link_label": None,
        "type": Command.INTERACTIVE,
    }
    CONN_BY_ID = {
        "label": "Connect by ID",
        "tooltip": "Connect to a server by Battlemetrics ID",
        "prompt": "Enter server ID",
        "link_label": "Open Battlemetrics",
        "type": Command.INTERACTIVE,
    }
    ADD_BY_IP = {
        "label": "Add server by IP",
        "tooltip": "Add a server by IP",
        "prompt": "Enter IP in IP:Queryport format (e.g. 192.168.1.1:27016)",
        "link_label": None,
        "type": Command.INTERACTIVE,
    }
    ADD_BY_ID = {
        "label": "Add server by ID",
        "tooltip": "Add a server by Battlemetrics ID",
        "prompt": "Enter server ID",
        "link_label": "Open Battlemetrics",
        "type": Command.INTERACTIVE,
    }
    CHNG_FAV = {
        "label": "Change favorite server",
        "tooltip": "Update your quick-connect server",
        "prompt": "Enter IP in IP:Queryport format (e.g. 192.168.1.1:27016)",
        "link_label": None,
        "alt": None,
        "default": "unset",
        "val": "fav_label",
        "type": Command.INTERACTIVE,
    }
    CHNG_PLAYER = {
        "label": "Change player name",
        "tooltip": "Update your in-game name (required by some servers)",
        "prompt": "Enter new nickname",
        "link_label": None,
        "alt": None,
        "default": None,
        "val": "name",
        "type": Command.INTERACTIVE,
    }
    CHNG_STEAM_API = {
        "label": "Change Steam API key",
        "tooltip": "Can be used if you revoked an old API key",
        "prompt": "Enter new API key",
        "link_label": "Open Steam API page",
        "type": Command.INTERACTIVE,
    }
    CHNG_BM_API = {
        "label": "Change Battlemetrics API key",
        "tooltip": "Can be used if you revoked an old API key",
        "link_label": "Open Battlemetrics API page",
        "prompt": "Enter new API key",
        "type": Command.INTERACTIVE,
    }

    # settings toggles
    TGL_BRANCH = {
        "label": "Toggle release branch",
        "tooltip": "Switch between stable and testing branches",
        "default": None,
        "val": "branch",
        "type": Command.TOGGLE,
    }
    TGL_INSTALL = {
        "label": "Toggle mod install mode",
        "tooltip": "Switch between manual and auto mod installation",
        "default": "manual",
        "link_label": "Open Steam Workshop",
        "alt": "auto",
        "val": "auto_install",
        "type": Command.TOGGLE,
    }
    TGL_STEAM = {
        "label": "Toggle Steam/Flatpak",
        "tooltip": "Switch the preferred client to use for launching DayZ",
        "alt": None,
        "default": None,
        "val": "preferred_client",
        "type": Command.TOGGLE,
    }
    TGL_FULLSCREEN = {
        "label": "Toggle DZGUI fullscreen boot",
        "tooltip": "Whether to start DZGUI as a maximized window (desktop only)",
        "alt": "true",
        "default": "false",
        "val": "fullscreen",
        "type": Command.TOGGLE,
    }

    # oneshot commands
    QUICK_CONNECT = {
        "label": "Quick-connect to favorite server",
        "tooltip": "Connect to your favorite server",
        "wait_msg": "Working",
        "default": "unset",
        "alt": None,
        "val": "fav_label",
        "type": Command.ONESHOT,
    }
    FORCE_UPDATE = {
        "label": "Force update local mods",
        "tooltip": "Synchronize local mods with remote versions (experimental)",
        "wait_msg": "Updating mods",
        "type": Command.ONESHOT,
    }
    DUMP_LOG = {
        "label": "Output system info to log file",
        "tooltip": "Dump diagnostic data for troubleshooting",
        "wait_msg": "Generating log",
        "type": Command.ONESHOT,
    }
    HANDSHAKE = {
        "label": "Handshake",
        "tooltip": None,
        "wait_msg": "Waiting for DayZ",
        "type": Command.ONESHOT,
    }
    HANDSHAKE_EXP = {
        "label": "Handshake_EXP",
        "tooltip": None,
        "wait_msg": "Waiting for DayZ",
        "type": Command.ONESHOT,
    }
    DELETE_SELECTED = {
        "label": "Delete selected mods",
        "tooltip": None,
        "wait_msg": "Deleting mods",
        "type": Command.ONESHOT,
    }

    # help pages
    DOCS = {
        "label": "Documentation/help files (GitHub) ⧉",
        "tooltip": "Opens the DZGUI documentation in a browser",
        "type": Command.HELP,
    }
    DOCS_FALLBACK = {
        "label": "Documentation/help files (Codeberg mirror) ⧉",
        "tooltip": "Opens the DZGUI documentation in a browser",
        "type": Command.HELP,
    }
    BUGS = {
        "label": "Report a bug (GitHub) ⧉",
        "tooltip": "Opens the DZGUI issue tracker in a browser",
        "type": Command.HELP,
    }
    FORUM = {
        "label": "DZGUI Subreddit ⧉",
        "tooltip": "Opens the DZGUI discussion forum in a browser",
        "type": Command.HELP,
    }
    SPONSOR = {
        "label": "Sponsor (GitHub) ⧉",
        "tooltip": "Sponsor the developer of DZGUI",
        "type": Command.HELP,
    }


class ContextMenu(EnumWithAttrs):
    """
    Calls methods defined in TreeView
    """

    ADD_SERVER = {"label": "Add to my servers", "action": "add_server"}
    REMOVE_SERVER = {
        "label": "Remove from my servers",
        "action": "remove_server",
    }
    COPY_NAME = {"label": "Copy name to clipboard", "action": "copy_name"}
    COPY_CLIPBOARD = {
        "label": "Copy IP to clipboard",
        "action": "copy_clipboard",
    }
    SHOW_MODS = {"label": "Show server-side mods", "action": "show_mods"}
    SHOW_DETAILS = {"label": "Server details", "action": "show_details"}
    REFRESH_PLAYERS = {
        "label": "Refresh player count",
        "action": "refresh_player_count",
    }
    REMOVE_HISTORY = {
        "label": "Remove from history",
        "action": "remove_from_history",
    }
    OPEN_WORKSHOP = {
        "label": "Open in Steam Workshop",
        "action": "open_workshop",
    }
    DELETE_MOD = {"label": "Delete mod", "action": "delete_mod"}


class WindowContext(EnumWithAttrs):
    @classmethod
    def row2con(cls, row: RowType) -> "WindowContext":
        m = WindowContext.MAIN_MENU
        for member in cls:
            if row in member.dict["rows"]:
                m = member
            elif row in member.dict["called_by"]:
                m = member
            else:
                continue
        return m

    # outer menu pages
    MAIN_MENU = {
        "label": "Main menu",
        "rows": [
            RowType.SERVER_BROWSER,
            RowType.SAVED_SERVERS,
            RowType.QUICK_CONNECT,
            RowType.RECENT_SERVERS,
            RowType.CONN_BY_IP,
            RowType.CONN_BY_ID,
            RowType.SCAN_LAN,
        ],
        "called_by": [],
    }
    MANAGE = {
        "label": "Manage",
        "rows": [
            RowType.ADD_BY_IP,
            RowType.ADD_BY_ID,
            RowType.CHNG_FAV,
            RowType.LIST_MODS,
        ],
        "called_by": [],
    }
    OPTIONS = {
        "label": "Options",
        "rows": [
            RowType.TGL_BRANCH,
            RowType.TGL_INSTALL,
            RowType.TGL_STEAM,
            RowType.TGL_FULLSCREEN,
            RowType.CHNG_PLAYER,
            RowType.CHNG_STEAM_API,
            RowType.CHNG_BM_API,
            RowType.FORCE_UPDATE,
        ],
        "called_by": [],
    }
    HELP = {
        "label": "Help",
        "rows": [
            RowType.CHANGELOG,
            RowType.SHOW_LOG,
            RowType.DUMP_LOG,
            RowType.DOCS,
            RowType.DOCS_FALLBACK,
            RowType.BUGS,
            RowType.FORUM,
            RowType.SPONSOR,
        ],
        "called_by": [],
    }

    # inner server contexts
    TABLE_API = {
        "label": "",
        "rows": [],
        "called_by": [RowType.SERVER_BROWSER],
    }
    TABLE_SERVER = {
        "label": "",
        "rows": [],
        "called_by": [
            RowType.SAVED_SERVERS,
            RowType.RECENT_SERVERS,
            RowType.SCAN_LAN,
        ],
    }
    TABLE_MODS = {
        "label": "",
        "rows": [],
        "called_by": [
            RowType.LIST_MODS,
        ],
    }
    TABLE_LOG = {
        "label": "",
        "rows": [],
        "called_by": [RowType.SHOW_LOG],
    }


class ButtonType(EnumWithAttrs):
    MAIN_MENU = {
        "label": "Main menu",
        "opens": WindowContext.MAIN_MENU,
        "tooltip": "Search for and connect to servers",
    }
    MANAGE = {
        "label": "Manage",
        "opens": WindowContext.MANAGE,
        "tooltip": "Manage/add to saved servers",
    }
    OPTIONS = {
        "label": "Options",
        "opens": WindowContext.OPTIONS,
        "tooltip": "Change settings, list local mods and\nother advanced options",
    }
    HELP = {
        "label": "Help",
        "opens": WindowContext.HELP,
        "tooltip": "Links to documentation",
    }
    EXIT = {"label": "Exit", "opens": None, "tooltip": "Quits the application"}


def is_navkey(key: int) -> bool:
    nav_keys = [
        Gdk.KEY_Down,
        Gdk.KEY_Up,
        Gdk.KEY_Page_Down,
        Gdk.KEY_Page_Up,
        Gdk.KEY_j,
        Gdk.KEY_k,
        Gdk.KEY_g,
        Gdk.KEY_G,
    ]
    if key in nav_keys:
        return True
    return False


def call_bash_func(command: str, arg: str) -> None:
    """
    Instantaneous system calls that open something
    in the background (xdg-open) or serialize a file quickly
    Contrast with call_out(), which should be called on a thread
    """
    subprocess.Popen(["/usr/bin/env", "bash", funcs, command, arg])


def load_css() -> None:
    css = """
    .frame {
        border: 0px;
    }
    .toast-label {
        padding: 10px;
    }
    .frame > border {
        border-radius: 5px;
        padding: 5px;
    }
    .page-heading {
        font-size: 1.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .settings-subheading {
        font-size: 1.2rem;
        font-weight: 700;
    }
    .left-label {
        font-size: 1.3rem;
    }
    .details-heading {
        font-size: 1.2rem
    }
    """
    prov = Gtk.CssProvider()
    prov.load_from_data(css.encode("ascii"))
    screen = Gdk.Screen.get_default()
    if screen:
        Gtk.StyleContext.add_provider_for_screen(
            screen, prov, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )


def add_class(widget: Gtk.Widget, label: str) -> None:
    """
    Sets the classname of a widget, used
    to apply CSS styling later
    """
    context = widget.get_style_context()
    context.add_class(label)


def unblock_signals() -> None:
    block_signals(False)


def block_signals(state: bool = True) -> None:
    suppress_signal(
        App.grid.right_panel.filters_vbox,
        App.grid.right_panel.filters_vbox.maps_combo,
        "_on_map_changed",
        state,
    )
    suppress_signal(
        App.treeview,
        App.treeview.selected_row,
        "_on_tree_selection_changed",
        state,
    )
    suppress_signal(App.treeview, App.treeview, "_on_keypress", state)
    for check in App.grid.right_panel.filters_vbox.checks:
        suppress_signal(
            App.grid.right_panel.filters_vbox,
            check,
            "_on_check_toggled",
            state,
        )


def save_res_and_quit(*args) -> None:
    if App.window.props.is_maximized:
        Gtk.main_quit()
        return
    rect = App.window.get_size()

    def write_json(rect):
        data = {"res": {"width": rect.width, "height": rect.height}}
        j = json.dumps(data, indent=2)
        with open(res_path, "w") as outfile:
            outfile.write(j)
        logger.info(f"Wrote window size to '{res_path}'")

    if os.path.isfile(res_path):
        with open(res_path, "r") as infile:
            try:
                data = json.load(infile)
                data["res"]["width"] = rect.width
                data["res"]["height"] = rect.height
                with open(res_path, "w") as outfile:
                    outfile.write(json.dumps(data, indent=2))
            except json.decoder.JSONDecodeError:
                logger.critical(f"JSON decode error in '{res_path}'")
                write_json(rect)
    else:
        write_json(rect)

    Gtk.main_quit()


def suppress_signal(
    owner: Gtk.Widget, widget: Gtk.Widget, func_name: str, state: bool
) -> None:

    func = getattr(owner, func_name)
    if state:
        logger.debug(f"Blocking {func_name} for {widget}")
        widget.handler_block_by_func(func)
    else:
        logger.debug(f"Unblocking {func_name} for {widget}")
        widget.handler_unblock_by_func(func)
    App.treeview.sel_blocked = state


def pluralize(plural: str, count: int) -> str:
    suffix = plural[-2:]
    if suffix == "es":
        base = plural[:-2]
        return f"{base}{'es'[:2*count ^ 2]}"
    else:
        base = plural[:-1]
        return f"{base}{'s'[:count ^ 1]}"


def format_metadata(row_sel: str) -> str:
    """
    Currently only being used for legacy
    favorite server tooltip, cf Statusbar.update_app_meta()
    """
    row = None
    for i in RowType:
        if i.dict["label"] == row_sel:
            row = i
            prefix = i.dict["tooltip"]
            break
    vals = {
        "branch": config_vals[0],
        "debug": config_vals[1],
        "auto_install": config_vals[2],
        "name": config_vals[3],
        "fav_label": config_vals[4],
        "preferred_client": config_vals[5],
        "fullscreen": config_vals[6],
        "default_steam_path": config_vals[7],
    }
    if row is None:
        return ""

    try:
        alt = row.dict["alt"]
        default = row.dict["default"]
        val = row.dict["val"]
    except KeyError:
        return prefix

    try:
        cur_val = vals[val]
        if cur_val == "":
            current = default
        elif cur_val == "1":
            current = alt
        else:
            current = cur_val
        return f"{prefix} | Current: '{current}'"
    except KeyError:
        return prefix


def signal_emission(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        block_signals()
        func(*args, **kwargs)
        unblock_signals()

    return wrapper


def update_window_labels(func: Callable) -> Callable:
    """
    Decorator that sets metadata on the
    current page context and subcontext
    """

    def wrapper(*args, **kwargs):
        if not App.ready:
            return
        func(*args, **kwargs)
        page_context = App.treeview.page.dict["label"]
        text = page_context
        App.window.hb.set_subtitle(page_context)

        if App.treeview.subpage == RowType.KEYBINDINGS:
            text = App.treeview.subpage.dict["label"]
        elif App.treeview.subpage:
            text = page_context + " > " + App.treeview.subpage.dict["label"]

        App.grid.set_breadcrumbs(text)
        App.grid.statusbar.refresh()

        logger.info(f"Window context changed to: {App.treeview.view}")
        logger.info(f"Page context changed to: {App.treeview.page}")
        logger.info(f"Subpage context changed to: {App.treeview.subpage}")

    return wrapper


def set_surrounding_margins(widget: Gtk.Widget, margin: int) -> None:
    """
    Utility function that sets all margins
    on a widget to a uniform integer value
    """
    widget.set_margin_top(margin)
    widget.set_margin_start(margin)
    widget.set_margin_end(margin)


def query_history() -> list | None:
    try:
        with open(history_file, "r") as f:
            rows = [row.rstrip("\n") for row in f]
    except OSError:
        rows = None
    finally:
        return rows


def query_favorites() -> None | list:
    proc = call_out("query_favorites")
    if proc.returncode == 1:
        return None
    rows = proc.stdout.splitlines()
    return rows


def query_config(key: str = "") -> list:
    proc = call_out("query_config", key)
    config = list(proc.stdout.splitlines())
    return config


def call_out(command: str, *args: str) -> subprocess.CompletedProcess:
    if hasattr(TreeView, "view"):
        name = getattr(TreeView, "view")
    else:
        name = "Generic"

    arg_ar = []
    for i in args:
        arg_ar.append(i)
    logger.info(
        f"Context '{name}' calling subprocess '{command}' with args '{arg_ar}'"
    )
    proc = subprocess.run(
        ["/usr/bin/env", "bash", funcs, command] + arg_ar,
        capture_output=True,
        text=True,
    )
    return proc


def spawn_dialog(msg: str, mode: Popup) -> bool:
    msg = textwrap.dedent(msg)
    dialog = GenericDialog(msg, mode)
    response = dialog.run()
    dialog.destroy()

    match response:
        case Gtk.ResponseType.OK:
            logger.info(f"User confirmed dialog with message '{msg}'")
            return False
        case Gtk.ResponseType.CANCEL | Gtk.ResponseType.DELETE_EVENT:
            logger.info(f"User aborted dialog with message '{msg}'")
            return True
    return False


def process_shell_return_code(
    msg: str, code: int, original_input: RowType
) -> None:
    logger.info(
        f"Processing return code '{code}' for the input "
        f"'{original_input}', returned message '{msg}'"
    )
    match code:
        case 0:  # success with notice popup
            spawn_dialog(msg, Popup.NOTIFY)
        case 1:  # error with notice popup
            if msg == "":
                msg = "Something went wrong"
            spawn_dialog(msg, Popup.NOTIFY)
        case 2:  # warn and recurse (e.g. validation failed)
            spawn_dialog(msg, Popup.NOTIFY)
            process_tree_option(original_input)
        case 4:  # for BM only
            spawn_dialog(msg, Popup.NOTIFY)
            process_tree_option(RowType.CHNG_BM_API)
        case 5:  # for steam only, deprecated
            spawn_dialog(msg, Popup.NOTIFY)
            process_tree_option(RowType.CHNG_STEAM_API)
        case 6:  # return silently
            pass
        case 78:  # failed settings update (steam)
            spawn_dialog("Invalid Steam API key, reverting", Popup.NOTIFY)
            App.notebook.settings.revert(Preferences.STEAM)
        case 79:  # failed settings update (bm)
            spawn_dialog(
                "Invalid Battlemetrics API key, reverting", Popup.NOTIFY
            )
            App.notebook.settings.revert(Preferences.BM)
        case 80:  # pop toast after successful settings change
            config_vals.clear()
            for i in query_config():
                config_vals.append(i)
            App.window.toast.set_text_and_fade("Settings updated!")
            App.notebook.settings.populate_settings()
        case 90:  # used to update configs and metadata in-place
            config_vals.clear()
            for i in query_config():
                config_vals.append(i)
            App.grid.statusbar.refresh()
            spawn_dialog(msg, Popup.NOTIFY)
            return
        case 95:  # successful mod deletion
            spawn_dialog(msg, Popup.NOTIFY)
            App.treeview._update_mod_store()
        case 96:  # unsuccessful mod deletion
            spawn_dialog(msg, Popup.NOTIFY)
            # re-block this signal before redrawing table contents
            suppress_signal(App.treeview, App.treeview, "_on_keypress", False)
            App.treeview.update_quad_column(RowType.LIST_MODS)
        case 99:  # highlight stale mods
            panel = App.grid.sel_panel
            panel.colorize_cells(True)
        case 100:  # final handshake before launch
            final_conf = spawn_dialog(msg, Popup.CONFIRM)
            if final_conf == 1 or final_conf is None:
                return
            process_tree_option(RowType.HANDSHAKE)
        case 101:  # final handshake, exp
            final_conf = spawn_dialog(msg, Popup.CONFIRM)
            if final_conf == 1 or final_conf is None:
                return
            process_tree_option(RowType.HANDSHAKE_EXP)
        case 255:  # dzgui version update
            msg = "Update complete. Please close DZGUI and restart."
            spawn_dialog(msg, Popup.QUIT)


def call_on_thread(
    state: bool, subproc: str, msg: str, args: str, choice: RowType = None
) -> None:
    """
    Exclusively used for threaded subprocesses
    """

    def _background(subproc: str, args: str, dialog):
        def _load() -> None:
            wait_dialog.destroy()
            out = proc.stdout.splitlines()
            try:
                msg = out[-1]
            except IndexError:
                msg = ""
            rc = proc.returncode
            logger.info(f"Subprocess returned code {rc} with message '{msg}'")
            process_shell_return_code(msg, rc, choice)

        proc = call_out(subproc, args)
        GLib.idle_add(_load)

    if state:
        wait_dialog = GenericDialog(msg, Popup.WAIT)
        wait_dialog.show_all()
        thread = threading.Thread(
            target=_background, args=(subproc, args, wait_dialog)
        )
        thread.start()
    else:
        """
        False is used to bypass wait dialogs;
        used by fast, one-shot processes
        """
        proc = call_out(subproc, args)
        rc = proc.returncode
        out = proc.stdout.splitlines()
        msg = out[-1]
        process_shell_return_code(msg, rc, choice)


def process_tree_option(choice: RowType) -> None:
    context = App.treeview.view
    command = choice
    cmd_string = command.dict["label"]
    logger.info(f"Parsing tree option '{command}' for the context '{context}'")

    # server tables
    if command == RowType.RESOLVE_IP:
        record = App.treeview.get_record_string()
        wait_msg = command.dict["wait_msg"]
        show_wait_dialog = True
        call_on_thread(
            show_wait_dialog, cmd_string, wait_msg, record, choice=choice
        )
        return

    # modlist highlight stale action
    if context == WindowContext.TABLE_MODS and command == RowType.HIGHLIGHT:
        wait_msg = command.dict["wait_msg"]
        show_wait_dialog = True
        call_on_thread(
            show_wait_dialog, cmd_string, wait_msg, "", choice=choice
        )
        return

    if command == RowType.CHANGELOG:
        App.grid.notebook.set_page_by_enum(NotebookPage.CHANGELOG)
        return

    if command == RowType.QUICK_CONNECT:
        record = query_config("fav_server")[0]
        if record == "":
            spawn_dialog("No favorite server currently set", Popup.NOTIFY)
            return

        record = str_to_record(record)
        thread_new_with_dialog(
            App.treeview.prepare_connection,
            parse_shell_output,
            "Querying server",
            command,
            [record],
        )
        return

    match command.dict["type"]:
        case Command.HELP:
            call_bash_func("Open link", cmd_string)
        case Command.TOGGLE:
            process_toggle(command)
        case Command.INTERACTIVE:
            process_user_input(command)
        case Command.ONESHOT:
            wait_msg = command.dict["wait_msg"]
            show_wait_dialog = True
            call_on_thread(show_wait_dialog, cmd_string, wait_msg, "")
        case _:
            return
    return


def parse_shell_output(proc: subprocess.CompletedProcess, row: RowType):
    out = proc.stdout.splitlines()
    try:
        msg = out[-1]
    except IndexError:
        msg = ""
    process_shell_return_code(msg, proc.returncode, row)


def thread_new_with_dialog(
    func: Callable,
    callback: Callable | None,
    msg: str,
    row: RowType | None,
    args: list,
) -> None:
    """
    Pop a GenericDialog transient to App.treeview and
    call a function on a thread, with optional callback.
    Chiefly used for connection-related subprocesses.

    After completion, the dialog is destroyed in the main event loop
    and additional exception handling occurs.

    This is intended as a bridge between legacy shell methods and the UI.
    A more abstracted version of call_on_thread() for when extra threaded
    processing occurs before calls to shell subprocesses.
    """

    def background(*args):
        def cleanup():
            App.treeview.dialog_hide()
            if exception is not None:
                spawn_dialog(str(exception), Popup.NOTIFY)
                process_user_input(row)
                return
            if callback is not None and proc is not None:
                callback(proc, row)

        exception = None
        proc = None
        try:
            proc = func(*args)
        except Exception as e:
            exception = e
            GLib.idle_add(cleanup)
            return
        GLib.idle_add(cleanup)

    App.treeview.dialog_show(msg)
    thread = threading.Thread(target=background, args=(args))
    thread.start()


def process_toggle(command: RowType) -> None:
    cmd_string = command.dict["label"]
    match command:
        case RowType.TGL_BRANCH:
            wait_msg = "Updating DZGUI branch"
            show_wait_dialog = False
            call_on_thread(show_wait_dialog, "toggle", wait_msg, cmd_string)
        case RowType.TGL_INSTALL:
            if query_config("auto_install")[0] == "1":
                proc = call_out("toggle", cmd_string)
                return
            # manual -> auto mode
            proc = call_out("find_id", "")
            if proc.returncode == 1:
                link = None
                user_id = ""
            else:
                link = command.dict["link_label"]
                user_id = proc.stdout
            LinkDialog(manual_sub_msg, link, command, user_id)
        case _:
            proc = call_out("toggle", cmd_string)


def str_to_record(record: str) -> Record | None:
    r = record.split(":")
    if len(r) != 3:
        return None
    return Record(r[0], int(r[1]), int(r[2]))


def record_to_str(record: Record) -> str:
    return f"{record.ip}:{record.gameport}:{record.qport}"


def connect_by_ip(enum: RowType, response: str) -> None:
    def _prep(response: str) -> None:
        record = Servers.validate_ip(response)
        proc = App.treeview.prepare_connection(record)
        return proc

    thread_new_with_dialog(
        _prep, parse_shell_output, "Querying IP", enum, [response]
    )
    return


def connect_by_id(enum: RowType, response: str, key: str) -> None:
    def _prep(key: str, response: str) -> None:
        record = Servers.query_bm_api(key, response)
        proc = App.treeview.prepare_connection(record)
        return proc

    thread_new_with_dialog(
        _prep, parse_shell_output, "Querying API", enum, [key, response]
    )
    return


def process_user_input(enum: RowType) -> None:
    prompt = enum.dict["prompt"]
    link_label = enum.dict["link_label"]
    cmd_string = enum.dict["label"]

    if enum == RowType.CONN_BY_ID:
        key = query_config("api_key")[0]
        if len(key) == 0:
            spawn_dialog(
                "No Battlemetrics API key is set; see Options", Popup.NOTIFY
            )
            return

    user_entry = EntryDialog(prompt, Popup.ENTRY, link_label)
    response = user_entry.get_input()

    if response is None:
        logger.info("User aborted entry dialog")
        return
    logger.info(f"User entered: '{response}'")

    if enum == RowType.CONN_BY_IP:
        connect_by_ip(enum, response)
        return

    if enum == RowType.CONN_BY_ID:
        connect_by_id(enum, response, key)
        return

    show_wait_dialog = True
    wait_msg = "Working"
    call_on_thread(
        show_wait_dialog, cmd_string, wait_msg, response, choice=enum
    )
    return


class OuterWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=app_name)
        App.ready = False

        self.hb = AppHeaderBar()

        # steam deck taskbar may occlude elements
        if not IS_STEAM_DECK:
            self.set_titlebar(self.hb)

        self.connect("delete-event", self._on_delete_event)
        self.connect("key-press-event", self._on_keypress)

        self.set_border_width(10)
        self._set_resolution()

        self.grid = Grid()
        self.toast = Toast()
        self.overlay = Gtk.Overlay()
        self.overlay.add_overlay(self.grid)
        self.overlay.add_overlay(self.toast)
        self.add(self.overlay)

        self.show_all()
        self.toast.set_visible(False)

        self.grid.right_panel.filters_vbox.set_visible(False)
        self.grid.right_panel.enable_ping_button(False)
        self.grid.sel_panel.set_visible(False)

        # convenience to avoid deep calls
        App.window = self
        App.grid = self.grid
        App.notebook = self.grid.notebook
        App.treeview = self.grid.scrollable_treelist.treeview
        App.right_panel = self.grid.right_panel

        load_css()
        App.ready = True
        App.grid.notebook.set_page_by_enum(NotebookPage.MAIN)
        App.treeview.grab_focus()

    def _on_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        if event.keyval is not Gdk.KEY_d:
            return
        if App.right_panel.filters_vbox.keyword_entry.is_focus():
            return
        if App.right_panel.filters_vbox.maps_entry.is_focus():
            return
        App.right_panel.toggle_debug()

    def _set_resolution(self) -> None:
        if IS_GAME_MODE is True:
            self.fullscreen()
            return
        elif query_config("fullscreen")[0] == "true":
            logger.info("User preference for 'fullscreen' is 'true'")
            self.fullscreen()

        try:
            with open(res_path, "r") as infile:
                try:
                    data = json.load(infile)
                    valid_json = True
                except json.decoder.JSONDecodeError:
                    logger.critical(f"JSON decode error in '{res_path}'")
                    valid_json = False
        except OSError:
            valid_json = False

        if valid_json:
            res = data["res"]
            w, h = res["width"], res["height"]
            logger.info(f"Restoring window size to {w},{h}")
            self.set_default_size(w, h)
        else:
            self.set_default_size(1400, 800)

    def _on_delete_event(
        self, window: "OuterWindow", event: Gdk.EventKey
    ) -> None:
        self.halt_proc_and_quit()

    def halt_proc_and_quit(self) -> None:
        App.grid.terminate_treeview_process()
        save_res_and_quit()


class Toast(Gtk.EventBox):
    def __init__(self):
        super().__init__()

        self.label = Gtk.Label()
        self.box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )
        self.box.add(self.label)
        self.add(self.box)
        self.box.set_size_request(200, 100)

        add_class(self.box, "toast-label")

    def set_text(self, text: str) -> None:
        self.label.set_text(text)

    def set_text_and_fade(self, text: str) -> None:
        self.set_text(text)
        self.pop()
        self._defer_fade()

    def fade_out(self) -> bool:
        if self.get_opacity() == 0:
            self.set_visible(False)
            self.set_opacity(1)
            return False
        self.set_opacity(self.get_opacity() - 0.03)
        return True

    def pop(self) -> None:
        self.set_visible(True)

    def _defer_fade(self) -> Literal[False]:
        GLib.timeout_add(30, self.fade_out)
        return False


class ScrollableTree(Gtk.ScrolledWindow):
    def __init__(self):
        super().__init__()

        self.treeview = TreeView()
        self.add(self.treeview)


class RightPanel(Gtk.Box):
    def __init__(self):
        super().__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL)

        self.button_vbox = ButtonBox()
        self.filters_vbox = FilterPanel()

        self.pack_start(self.button_vbox, False, False, 0)
        self.pack_start(self.filters_vbox, False, False, 0)

        debug_tooltip = (
            "Used to perform a dry run without\n"
            "actually connecting to a server"
        )
        ping_tooltip = (
            "Refresh the ping for visible servers.\n"
            "Available once per unique filter context"
        )

        self.ping = Gtk.Button(
            label="Ping servers",
            margin_top=10,
            margin_start=80,
            margin_end=80,
            tooltip_text=ping_tooltip,
        )
        self.ping.connect("clicked", self._on_ping_clicked)

        self.debug_toggle = Gtk.ToggleButton(
            label="Debug mode",
            margin_top=10,
            margin_start=80,
            margin_end=80,
            tooltip_text=debug_tooltip,
        )

        if query_config("debug")[0] == "1":
            self.debug_toggle.set_active(True)
        self.debug_toggle.connect("toggled", self._on_debug_toggled)

        self.question = Gtk.Button(
            label="?",
            margin_top=10,
            margin_start=80,
            margin_end=80,
            tooltip_text="Opens the keybindings dialog",
        )
        self.question.connect("clicked", self._on_question_clicked)

        self.pack_start(self.ping, False, True, 0)
        self.pack_start(self.debug_toggle, False, True, 0)
        self.pack_start(self.question, False, True, 0)

    def enable_ping_button(self, state: bool) -> None:
        self.ping.set_visible(state)

    def reinit_maps(self, rows: list) -> None:
        map_store.clear()
        map_store.append(["All maps"])
        self.selected = "All maps"
        self.filters_vbox.set_unique_maps(rows)

    def toggle_debug(self) -> None:
        if type(App.window.get_focus()) is Gtk.Entry:
            return
        state = self.debug_toggle.get_active()
        self.debug_toggle.set_active(not state)

    def _on_debug_toggled(self, button: Gtk.Button) -> None:
        grid = App.grid
        call_out("toggle", "Toggle debug mode")
        grid.statusbar.refresh()
        App.grid.notebook.focus_current()

    def _on_ping_clicked(self, button: Gtk.Button) -> None:
        block_signals()

        def _update_pings():
            rows = ModelManager.get_filtered()
            with ThreadPoolExecutor(100) as executor:
                futures = [
                    executor.submit(Servers.ping, i, row)
                    for i, row in enumerate(rows)
                ]
                wait(futures)
                for future in futures:
                    res = future.result()
                    path = Gtk.TreePath.new_from_indices([res.iteration])
                    temp_model[path][9] = res.ping
                    ModelManager.ping_cache[res.addr] = res.ping
            App.treeview.set_model(temp_model)
            App.treeview.wait_dialog.destroy()
            App.treeview.enable_ping_column(True)
            App.treeview.grab_focus()
            App.right_panel.ping.set_sensitive(False)

            unblock_signals()

        temp_model = App.treeview.get_model()
        App.treeview.set_model(None)
        App.treeview.wait_dialog = GenericDialog("Pinging servers", Popup.WAIT)
        App.treeview.wait_dialog.show_all()
        thread = threading.Thread(target=_update_pings, args=())
        thread.start()

    def _on_question_clicked(self, button: Gtk.Button) -> None:
        App.grid.notebook.toggle_keybindings()

    def focus_button_box(self) -> None:
        self.button_vbox.buttons[0].grab_focus()


class ButtonBox(Gtk.Box):
    def __init__(self):
        super().__init__(
            spacing=6,
            margin_top=0,
            margin_start=10,
            margin_end=10,
            orientation=Gtk.Orientation.VERTICAL,
        )

        self.buttons = list()
        self.connect("key-press-event", self._on_keypress)

        for side_button in ButtonType:
            button = Gtk.Button(label=side_button.dict["label"])
            button.type = side_button
            button.set_tooltip_text(side_button.dict["tooltip"])

            if IS_STEAM_DECK:
                button.set_size_request(10, 10)
            else:
                button.set_size_request(50, 50)
            self.buttons.append(button)
            button.connect("clicked", self._on_selection_button_clicked)
            self.pack_start(button, False, False, 0)

    @signal_emission
    def _on_selection_button_clicked(self, button: Gtk.Button) -> None:
        context = button.type
        logger.info(f"User clicked '{context}'")

        if context == ButtonType.EXIT:
            logger.info("Normal user exit")
            save_res_and_quit()
            return

        if context == ButtonType.OPTIONS:
            App.notebook.settings.populate_settings()
            App.notebook.set_page_by_enum(NotebookPage.OPTIONS)
            return

        cols = App.treeview.get_columns()
        if len(cols) > 1:
            # restores tree from multi column view to main menu
            App.treeview.update_single_column(context)
            return

        App.treeview._populate(context.dict["opens"])
        cols[0].set_title(context.dict["label"])

    def _walk_buttons(self, increment: int) -> None:
        for i, button in enumerate(self.buttons):
            if button.is_focus():
                n = i + increment
                if n == len(self.buttons):
                    return
                if n == -1:
                    return
                n = self.buttons[n]
                n.grab_focus()
                return

    def _on_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        match event.keyval:
            case Gdk.KEY_h:
                App.notebook.focus_current()
            case Gdk.KEY_j:
                self._walk_buttons(1)
            case Gdk.KEY_k:
                self._walk_buttons(-1)
            case Gdk.KEY_question:
                App.grid.notebook.toggle_keybindings()


class CalcDist(multiprocessing.Process):
    def __init__(
        self,
        widget: Gtk.Widget,
        addr: str,
        result_queue: multiprocessing.Queue,
        cache: dict,
    ):
        super().__init__()

        self.widget = widget
        self.result_queue = result_queue
        self.addr = addr
        self.ip = addr.split(":")[0]

    def run(self) -> None:
        if self.addr in cache:
            logger.info(f"Address '{self.addr}' already in cache")
            self.result_queue.put([self.addr, cache[self.addr]])
            return
        proc = call_out("get_dist", self.ip)
        km = proc.stdout
        self.result_queue.put([self.addr, km])


class ModelManagerSingleton:
    """
    Manages access to ListStore cache resources and
    performs filtering on behalf of TreeView.

    Filtration to and from ListStore format is
    delegated to this singleston.

    Not thread-safe.
    """

    def __init__(self):
        # packed ListStores
        self.filter_cache = {}
        self.ping_cache = {}
        # stringwise (list) representation of the model
        self.control_model = None
        self.filtered = None
        self.success = True

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(ModelManagerSingleton, cls).__new__(cls)
        return cls.instance

    def filter(self, mode: FilterMode, *args, **kwargs) -> None:
        """
        Native Gtk.TreeView.refilter() method was not performant enough
        when running in the main loop with 40k+ records
        """
        filters = App.right_panel.filters_vbox.get_filters()

        if filters in self.filter_cache:
            cache = self.filter_cache[filters]
            self.set_store(cache[0])
            self.set_filtered(cache[1])
            GLib.idle_add(App.treeview._filter_cleanup)
            return

        match mode:
            case FilterMode.INITIAL:
                rows = self.filter_initial(filters)

            case FilterMode.MAP:
                panel = App.right_panel.filters_vbox
                prior_map = panel.get_prior_map()

                if prior_map == "All maps":
                    rows = self.filter_map(filters)
                else:
                    App.right_panel.ping.set_sensitive(True)
                    rows = self.filter_toggle_on(filters, *args)

            case FilterMode.KEYWORD:
                App.right_panel.ping.set_sensitive(True)
                rows = self.filter_toggle_on(filters, *args)

            case FilterMode.TOGGLE_OFF:
                for f in filters[2:]:
                    self.set_filtered(self.filter_toggle_off(filters, f))
                rows = self.filtered

            case FilterMode.TOGGLE_ON:
                App.right_panel.ping.set_sensitive(True)
                rows = self.filter_toggle_on(filters, *args)

        if mode is not FilterMode.INITIAL:
            for row in rows:
                if row[7] in self.ping_cache:
                    row[9] = self.ping_cache[row[7]]

        if len(rows) > 0:
            clone = ModelManager.new_model()
            rows = self.sort_rows(rows)
            for row in rows:
                clone.append(row)
        else:
            clone = None

        self.set_cache(filters, clone, rows)
        self.set_store(clone)
        GLib.idle_add(App.treeview._filter_cleanup)

    def sort_rows(self, rows: list) -> list:
        rows.sort(key=lambda x: re.sub(r"[^A-Za-z0-9]+", "", x[0].lower()))
        return rows

    def filter_initial(self, filters: tuple) -> list:
        """
        Simply culls the control model of any disabled filters
        """
        self.set_filtered(self.control_model)
        for f in filters[2:]:
            self.set_filtered(self.filter_toggle_off(filters, f))
        return self.filtered

    def filter_map(self, filters: tuple) -> list:
        """
        Multi-filtration for any context starts by narrowing by map
        """
        rows = self.filtered
        panel = App.right_panel.filters_vbox
        sel_map = panel.get_selected_map()

        if sel_map == "All maps":
            return rows

        rows = [row for row in rows if row[1] == sel_map]
        return rows

    def filter_keyword(self, filters: tuple) -> list:
        keyword = App.right_panel.filters_vbox.get_keyword_filter()
        rows = self.filtered

        if keyword == "":
            return rows

        filtered = [
            row
            for row in rows
            if keyword in row[0].lower()
            or keyword in row[1].lower()
            or keyword in row[7].lower()
        ]
        return filtered

    def filter_toggle_off(self, filters: tuple, filter_type: str) -> list:
        """
        Sub-filtration of the current model
        """
        pairs = {"3PP": "1PP", "Day": "Night", "Official": "Unoffic."}
        for k, v in pairs.items():
            if k in filters and v in filters:
                self.set_filtered(None)
                return []

        rows = self.filtered
        match filter_type:
            case "3PP":
                rows = [row for row in rows if row[2] != "3PP"]
            case "1PP":
                rows = [row for row in rows if row[2] != "1PP"]
            case "Official":
                rows = [row for row in rows if row[10] != "Official"]
            case "Unoffic.":
                rows = [row for row in rows if row[10] != "Unoffic."]
            case "Empty":
                rows = [row for row in rows if row[4] != 0]
            case "Full":
                rows = [row for row in rows if row[4] != row[5]]
            case "Duplicate":
                seen = []
                final = []
                for row in rows:
                    if row[0] in seen:
                        continue
                    seen.append(row[0])
                    final.append(row)
                rows = final
            case "Day":
                reg = r"([0][0-9]|[1][0-6])"
                rows = [row for row in rows if not re.match(reg, row[3])]
            case "Night":
                reg = r"([0][0-4]|[1][8]|[2][0-3])"
                rows = [row for row in rows if not re.match(reg, row[3])]
            case "Non-ASCII":
                rows = [row for row in rows if row[0].isascii()]
            case "Low pop":
                rows = [row for row in rows if (row[4] / row[5] * 100) > 30]
            case "Modded":
                rows = [row for row in rows if not row[11]]
        return rows

    def filter_toggle_on(self, filters: tuple, *args: str) -> list:
        """Effectively applies all filters"""
        self.set_filtered(self.control_model)
        self.set_filtered(self.filter_map(filters))
        self.set_filtered(self.filter_keyword(filters))

        for f in filters[2:]:
            self.set_filtered(self.filter_toggle_off(filters, f))
        return self.filtered

    def set_cache(
        self, filters: tuple, model: Gtk.ListStore | None, rows: list
    ) -> None:
        self.filter_cache[filters] = (model, rows)

    def new_model(self) -> Gtk.ListStore:
        return Gtk.ListStore(
            str, str, str, str, int, int, int, str, int, int, str, bool
        )

    def resync_model(self, addr: str, qport: int) -> None:
        """Handle in-situ updates to model during
        row deletion actions. Skipped for ephemeral
        actions like player count/ping updates
        """
        for row in self.control_model:
            if row[7] == addr and row[8] == qport:
                self.control_model.remove(row)

        self.wipe_cache()
        filters = App.right_panel.filters_vbox.get_filters()
        refiltered = self.filter_toggle_on(filters)
        self.set_filtered(refiltered)
        self.set_success(True)
        GLib.idle_add(App.treeview._filter_cleanup)

    def convert_model_to_list(self, model: Gtk.ListStore) -> list:
        return [[el for el in row] for row in model]

    def set_filtered(self, rows: list | None) -> None:
        if rows is None:
            rows = []
        self.filtered = rows

    def get_filtered(self) -> list:
        return self.filtered

    def set_store(self, model: Gtk.ListStore | None) -> None:
        self.store = model

    def get_store(self) -> Gtk.ListStore | None:
        return self.store

    def set_control(self, rows: list) -> None:
        self.control_model = rows

    def set_success(self, result: bool) -> None:
        self.success = result

    def get_success(self) -> bool:
        return self.success

    def wipe_cache(self, full=False) -> None:
        self.success = True
        self.filtered = None
        self.filter_cache = {}
        self.ping_cache = {}
        if full:
            self.control_model = None


class TreeView(Gtk.TreeView):
    __gsignals__ = {
        "on_distcalc_started": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self):
        super().__init__()

        """
        Since some views like TABLE_SERVER recycle
        the same model type, self.view corresponds
        to an enumeration of the current model in the tree.

        By contrast, self.page and self.subpage
        correspond to user-facing navigation contexts, e.g.,
        Main menu (page) > Server browser (subpage)

        This is used by:
        - logs
        - labels like breadcrumbs and the headerbar subtitle
        - methods passing contextual "you are here" info to helpers

        When on a top-level menu (WindowContext.MAIN_MENU),
        the subpage is None.
        """

        self.view = WindowContext.MAIN_MENU
        self.page = WindowContext.MAIN_MENU
        self.subpage = None
        self.sel_blocked = False

        self.set_fixed_height_mode(True)

        self.queue = multiprocessing.Queue()
        self.current_proc = None

        # disables typeahead search
        self.set_enable_search(False)
        self.set_search_column(-1)

        # populate model with initial context
        for row in WindowContext.MAIN_MENU.dict["rows"]:
            label = row.dict["label"]
            t = (label,)
            row_store.append(t)
        self.set_model(row_store)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Main menu", renderer, text=0)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.append_column(column)

        self.set_headers_visible(False)

        self.selected_row = self.get_selection()
        self.selected_row.connect("changed", self._on_tree_selection_changed)
        self.connect("button-release-event", self._on_button_release)
        self.connect("row-activated", self._on_row_activated)

        self.connect("key-press-event", self._on_keypress)
        self.connect("key-release-event", self._on_key_release)

    def _update_mod_store(self) -> None:
        (model, pathlist) = self.get_selection().get_selected_rows()
        for p in reversed(pathlist):
            it = model.get_iter(p)
            model.remove(it)
        total_size = 0
        total_mods = len(model)
        for row in model:
            total_size += row[3]
        size = locale.format_string("%.3f", total_size, grouping=True)
        pretty = pluralize("mods", total_mods)
        App.grid.statusbar.set_text(
            f"Found {total_mods:n} {pretty} taking up {size} MiB"
        )
        # untoggle selection for visibility of other stale rows
        self.toggle_selection(False)

    def get_subpage_label(self) -> None:
        if self.subpage:
            return self.subpage.dict["label"]
        return None

    def get_subpage(self) -> RowType:
        return self.subpage

    def terminate_process(self) -> None:
        if self.current_proc and self.current_proc.is_alive():
            self.current_proc.terminate()

    def copy_name(self) -> None:
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        record = self.get_name()
        self.clipboard.set_text(record, -1)

    def copy_clipboard(self) -> None:
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        record = self.get_record_string()
        self.clipboard.set_text(record, -1)

    def delete_mod(self) -> None:
        modname = self.get_value_at_index(0)
        conf_msg = f"Really delete the mod '{modname}'?"
        res = spawn_dialog(conf_msg, Popup.CONFIRM)
        if res:
            return
        mods = []
        symlink = self.get_value_at_index(1)
        path = self.get_value_at_index(2)
        concat = symlink + " " + path + "\n"
        mods.append(concat)
        with open(mods_temp_file, "w") as outfile:
            outfile.writelines(mods)
        process_tree_option(RowType.DELETE_SELECTED)

    def open_workshop(self) -> None:
        record = self.get_value_at_index(2)
        base_cmd = "open_workshop_page"
        call_bash_func(base_cmd, record)

    def add_server(self) -> None:
        process_tree_option(RowType.RESOLVE_IP)

    def remove_server(self) -> None:
        """
        Both add and remove server functionally
        call the same logic in helpers/funcs;
        if the record exists, it is removed, and vice versa.
        When removing, the model needs to be updated in situ
        if the current context is RowType.SAVED_SERVERS
        """
        self.add_server()

        if self.subpage != RowType.SAVED_SERVERS:
            return

        self.resync_with_manager()

    def resync_with_manager(self):
        model = self.get_model()
        it = self.get_current_iter()
        if it:
            addr = model.get_value(it, 7)
            qport = model.get_value(it, 8)
            model.remove(it)

        block_signals()
        thread = threading.Thread(
            target=ModelManager.resync_model, args=(addr, qport)
        )
        thread.start()

    def remove_from_history(self) -> None:
        record = self.get_record_string()
        call_out("Remove from history", record)
        self.resync_with_manager()

    def show_details(self) -> None:
        model = self.get_model()
        it = self.get_current_iter()
        name = model.get_value(it, 0)
        record = self.get_record_dict()
        DetailsDialog(name, record.ip, record.qport)

    def show_mods(self) -> None:
        record = self.get_record_string()
        ModDialog(record)
        modlist_store.clear()

    def _on_menu_click(self, menu_item: Gtk.MenuItem) -> None:
        if hasattr(TreeView, menu_item.action):
            func = getattr(TreeView, menu_item.action)
            msg = (
                f"User clicked context menu '{menu_item.get_label()}', "
                f"calls {func}"
            )
            logger.info(msg)
            func(self)
        else:
            msg = (
                f"Context menu function for '{menu_item.action}' "
                f"does not exist"
            )
            u_msg = (
                f"Something went wrong when accessing the method "
                f"'{menu_item.action}'"
            )
            logger.critical(msg)
            spawn_dialog(u_msg, Popup.NOTIFY)
        return

    def toggle_selection(self, state: bool) -> None:
        for i, rows in enumerate(mod_store):  # type: ignore
            path = Gtk.TreePath.new_from_indices([i])
            if state:
                self.get_selection().select_path(path)
            else:
                self.get_selection().unselect_path(path)

    def has_mods(self) -> bool:
        select = self.get_selection()
        sels = select.get_selected_rows()
        (model, pathlist) = sels
        path = pathlist[0]
        tree_iter = model.get_iter(path)
        mods = model.get_value(tree_iter, 11)
        return mods

    def is_in_favs(self) -> bool:
        record = self.get_record_string()
        proc = call_out("is_in_favs", record)
        if proc.returncode == 0:
            return True
        return False

    def is_selection_empty(self) -> bool:
        sel = self.get_selection()
        sels = sel.get_selected_rows()
        (model, pathlist) = sels
        if len(pathlist) < 1:
            return True
        return False

    def _on_button_release(
        self, widget: Gtk.Widget, event: Gdk.EventButton
    ) -> None:
        if event.type is Gdk.EventType.BUTTON_RELEASE and event.button != 3:
            return

        try:
            pathinfo = self.get_path_at_pos(int(event.x), int(event.y))
            if pathinfo is None:
                return
            (path, col, cellx, celly) = pathinfo
            if path is None:
                return
            self.set_cursor(path, col, False)
        except AttributeError:
            pass

        self.menu = Gtk.Menu()
        mod_context_items = [ContextMenu.OPEN_WORKSHOP, ContextMenu.DELETE_MOD]
        server_context_items = {
            RowType.SERVER_BROWSER: [
                ContextMenu.ADD_SERVER,
                ContextMenu.COPY_NAME,
                ContextMenu.COPY_CLIPBOARD,
                ContextMenu.SHOW_MODS,
                ContextMenu.SHOW_DETAILS,
                ContextMenu.REFRESH_PLAYERS,
            ],
            RowType.SCAN_LAN: [
                ContextMenu.COPY_NAME,
                ContextMenu.COPY_CLIPBOARD,
                ContextMenu.SHOW_MODS,
                ContextMenu.SHOW_DETAILS,
                ContextMenu.REFRESH_PLAYERS,
            ],
            RowType.SAVED_SERVERS: [
                ContextMenu.REMOVE_SERVER,
                ContextMenu.COPY_NAME,
                ContextMenu.COPY_CLIPBOARD,
                ContextMenu.SHOW_MODS,
                ContextMenu.SHOW_DETAILS,
                ContextMenu.REFRESH_PLAYERS,
            ],
            RowType.RECENT_SERVERS: [
                ContextMenu.ADD_SERVER,
                ContextMenu.REMOVE_HISTORY,
                ContextMenu.COPY_NAME,
                ContextMenu.COPY_CLIPBOARD,
                ContextMenu.SHOW_MODS,
                ContextMenu.SHOW_DETAILS,
                ContextMenu.REFRESH_PLAYERS,
            ],
        }

        if self.view == WindowContext.TABLE_MODS:
            items = mod_context_items
        elif self.subpage in server_context_items:
            items = server_context_items[self.subpage]
        else:
            return

        for row in items:
            if row == ContextMenu.ADD_SERVER:
                if self.is_in_favs():
                    row = ContextMenu.REMOVE_SERVER
            item = Gtk.MenuItem(label=row.dict["label"])
            item.type = row
            item.action = row.dict["action"]
            item.connect("activate", self._on_menu_click)
            self.menu.append(item)
            if row == ContextMenu.SHOW_MODS:
                if not self.has_mods():
                    item.set_sensitive(False)
        self.menu.show_all()

        if event.type is Gdk.EventType.KEY_PRESS and event.keyval is Gdk.KEY_l:
            if self.is_selection_empty():
                return
            self.menu.popup_at_widget(
                widget, Gdk.Gravity.CENTER, Gdk.Gravity.WEST
            )
        else:
            self.menu.popup_at_pointer(event)
        self.menu.select_first(False)

    def refresh_player_count(self) -> None:
        if not self.is_server_context(self.view):
            return
        cooldown = call_out("test_cooldown", "", "")
        if cooldown.returncode == 1:
            spawn_dialog(cooldown.stdout, Popup.NOTIFY)
            return None
        call_out("start_cooldown", "", "")

        thread = threading.Thread(
            target=self._background_player_count, args=()
        )
        thread.start()

    def get_current_iter(self) -> Gtk.TreeIter | None:
        it = self.get_selection().get_selected()[1]
        return it

    def _on_tree_selection_changed(self, selection: Gtk.TreeSelection) -> None:
        # bail out on early init
        if not hasattr(App, "grid"):
            return
        grid = App.grid

        context = App.treeview.get_subpage_label()
        row_sel = self.get_value_at_index(0)
        logger.info(
            f"Tree selection for context '{context}' changed to '{row_sel}'"
        )

        if self.current_proc and self.current_proc.is_alive():
            self.current_proc.terminate()

        if (
            self.view == WindowContext.TABLE_API
            or self.view == WindowContext.TABLE_SERVER
        ):
            record = self.get_record_dict()
            if not record:
                grid.statusbar.update_server_meta()
                return
            ip = record.ip
            if ip in cache:
                km = cache[ip]
                grid.statusbar.append_distance(km)
                return
            self.emit("on_distcalc_started")
            self.current_proc = CalcDist(self, ip, self.queue, cache)
            self.current_proc.start()
        else:
            grid.statusbar.refresh()

    def get_selected_row_index(self) -> int:
        sel = self.get_selection()
        rows = sel.get_selected_rows()
        cur_row = rows[1][0][0]
        return cur_row

    def _move_cursor(self, position: CursorPosition) -> bool | None:
        cur_row = self.get_selected_row_index()
        model = self.get_model()
        if model:
            end = len(model) - 1
        else:
            return None

        if position == CursorPosition.DOWN:
            if cur_row == end:
                return True
            dest = cur_row + 1
        if position == CursorPosition.UP:
            if cur_row == 0:
                return True
            dest = cur_row - 1
        if position == CursorPosition.TOP:
            if cur_row == 0:
                return True
            dest = 0
        if position == CursorPosition.BOTTOM:
            if cur_row == end:
                return True
            dest = end
        path = Gtk.TreePath.new_from_indices([dest])
        self.set_cursor(path)
        return None

    def _on_keypress(
        self, treeview: Gtk.TreeView, event: Gdk.EventKey
    ) -> bool | None:
        keyname = Gdk.keyval_name(event.keyval)
        grid = App.grid
        if event.state is Gdk.ModifierType.CONTROL_MASK:
            match event.keyval:
                case Gdk.KEY_l:
                    self._on_button_release(self, event)
                case Gdk.KEY_r:
                    self.refresh_player_count()
                case Gdk.KEY_f:
                    if not App.treeview.is_server_context(App.treeview.view):
                        return True
                    App.right_panel.filters_vbox.keyword_entry.grab_focus()
                case Gdk.KEY_m:
                    if App.treeview.view == WindowContext.TABLE_MODS:
                        return True
                    App.right_panel.filters_vbox.maps_entry.grab_focus()
                case _:
                    return False
        else:
            if is_navkey(event.keyval):
                if self.sel_blocked is False:
                    suppress_signal(
                        App.treeview,
                        App.treeview.selected_row,
                        "_on_tree_selection_changed",
                        True,
                    )
            if keyname.isnumeric() and int(keyname) > 0:
                digit = int(keyname) - 1
                grid.right_panel.filters_vbox.toggle_check(digit)
                return False
            if event.keyval == Gdk.KEY_G:
                self._move_cursor(CursorPosition.BOTTOM)
            match event.keyval:
                case Gdk.KEY_g:
                    self._move_cursor(CursorPosition.TOP)
                case Gdk.KEY_j:
                    self._move_cursor(CursorPosition.DOWN)
                case Gdk.KEY_k:
                    self._move_cursor(CursorPosition.UP)
                case Gdk.KEY_l | Gdk.KEY_Right:
                    if event.state is Gdk.ModifierType.CONTROL_MASK:
                        return
                    App.right_panel.focus_button_box()
                case Gdk.KEY_0:
                    grid.right_panel.filters_vbox.toggle_check(9)
                case Gdk.KEY_minus:
                    grid.right_panel.filters_vbox.toggle_check(10)
                case Gdk.KEY_backslash:
                    grid.right_panel.filters_vbox.toggle_check(11)
                case _:
                    return False
        return None

    def _on_key_release(
        self, treeview: Gtk.TreeView, event: Gdk.EventKey
    ) -> None:
        """
        Suppresses spamming on keydown
        """
        if is_navkey(event.keyval):
            if self.sel_blocked is True:
                suppress_signal(
                    App.treeview,
                    App.treeview.selected_row,
                    "_on_tree_selection_changed",
                    False,
                )
            selection = self.get_selection()
            self._on_tree_selection_changed(selection)

    def focus_first_row(self) -> None:
        path = Gtk.TreePath.new_from_indices([0])
        try:
            self.get_selection().select_path(path)
        except ValueError:
            pass

    def get_value_at_index(self, index: int) -> str:
        select = self.get_selection()
        sels = select.get_selected_rows()
        (model, pathlist) = sels
        if len(pathlist) < 1:
            return ""
        path = pathlist[0]
        tree_iter = model.get_iter(path)
        value = model.get_value(tree_iter, index)
        return value

    def get_name(self) -> str:
        name = self.get_value_at_index(0)
        return name

    def get_record_string(self) -> str:
        addr = self.get_value_at_index(7)
        qport = self.get_value_at_index(8)
        return f"{addr}:{qport}"

    def get_record_dict(self) -> dict | None:
        select = self.get_selection()
        sels = select.get_selected_rows()
        (model, pathlist) = sels
        if len(pathlist) < 1:
            return None
        path = pathlist[0]
        model = self.get_model()
        if not model:
            return None
        addr = model[path][7]
        qport = model[path][8]
        ip = addr.split(":")[0]
        gameport = int(addr.split(":")[1])
        return Record(ip, gameport, qport)

    def update_players(self, players: int) -> None:
        model = self.get_model()
        path = self.get_mpath()
        if not model:
            return
        if not path:
            return
        model[path][4] = players

    def update_queue(self, players: int) -> None:
        model = self.get_model()
        path = self.get_mpath()
        model[path][6] = players

    def enable_ping_column(self, state: bool) -> None:
        columns = self.get_columns()
        for column in columns:
            if column.get_title() == "Ping":
                column.set_visible(state)

    def select_first_row(self):
        sel = self.get_selection()
        self._on_tree_selection_changed(sel)

    def get_mpath(self) -> Gtk.TreePath | None:
        select = self.get_selection()
        sels = select.get_selected_rows()
        (model, pathlist) = sels
        if len(pathlist) < 1:
            return None
        path = pathlist[0]
        return path

    def _background_player_count(self) -> None:
        def _load():
            lines = data.stdout.splitlines()
            self.update_players(int(lines[0]))
            self.update_queue(int(lines[1]))
            wait_dialog.destroy()

        wait_dialog = GenericDialog("Refreshing player count", Popup.WAIT)
        wait_dialog.show_all()
        record = self.get_record_dict()
        if not record:
            return
        data = call_out("get_player_count", record.ip, str(record.qport))
        if data.returncode == 1:
            wait_dialog.destroy()
            return
        GLib.idle_add(_load)

    def _dump_api(self):
        key = query_config("steam_api")[0]
        job = Servers.query_api
        params = Servers.params
        serv = []
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(job, key, APPID_DAYZ, param)
                for param in params
            ]
            wait(futures)
            for future in futures:
                res = future.result()
                if res.status != 200 or not res.parsed:
                    ModelManager.set_store(None)
                    ModelManager.set_success(False)
                    GLib.idle_add(self._filter_cleanup)
                    return
                j = res.json
                serv += j["response"]["servers"]

        res = Servers.query_api(key, APPID_DAYZ_EXP, "")
        if res.status == 200 and res.parsed is True:
            j = res.json
            serv += j["response"]["servers"]

        parsed = Servers.parse_json(serv)
        return parsed

    def _dump_lan(self, port: int) -> list | None:
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(Servers.test_ip, i, port)
                for i in range(1, 256)
            ]
            wait(futures)
            servers = []
            for future in futures:
                res = future.result()
                if res is None:
                    continue
                servers.append(res)
            if len(servers) == 0:
                ModelManager.set_store(None)
                ModelManager.set_success(False)
                GLib.idle_add(self._filter_cleanup)
                return None
            parsed = Servers.parse_json(servers)
        return parsed

    def _dump_servers(self, ips: list) -> list | None:
        if len(ips) == 0:
            return []
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    Servers.query_direct,
                    ip.split(":")[0],
                    int(ip.split(":")[2]),
                )
                for ip in ips
            ]
            wait(futures)
            serv = []
            for future in futures:
                res = future.result()
                if res is None:
                    continue
                serv.append(res)
            if len(serv) == 0:
                ModelManager.set_store(None)
                ModelManager.set_success(False)
                GLib.idle_add(self._filter_cleanup)
                return None
            parsed = Servers.parse_json(serv)
        return parsed

    def _query_servers(self, mode: RowType, port: int = 27016) -> None:
        block_signals()

        match mode:
            case RowType.SCAN_LAN:
                parsed = self._dump_lan(port)
            case RowType.SERVER_BROWSER:
                App.treeview.enable_ping_column(False)
                App.right_panel.enable_ping_button(True)
                parsed = self._dump_api()
            case RowType.SAVED_SERVERS:
                App.treeview.enable_ping_column(True)
                favs = query_favorites()
                if not favs:
                    ModelManager.set_success(False)
                    ModelManager.set_store(None)
                    GLib.idle_add(self._filter_cleanup)
                    return
                parsed = self._dump_servers(favs)
            case RowType.RECENT_SERVERS:
                App.treeview.enable_ping_column(True)
                history = query_history()
                if not history:
                    ModelManager.set_success(False)
                    ModelManager.set_store(None)
                    GLib.idle_add(self._filter_cleanup)
                    return
                parsed = self._dump_servers(history)

        if parsed is None:
            return
        App.right_panel.reinit_maps(parsed)

        # intialize to empty
        ModelManager.set_store(None)
        ModelManager.set_control(parsed)
        ModelManager.filter(FilterMode.INITIAL)

    def _filter_cleanup(self, empty: bool = False) -> None:
        model = ModelManager.get_store()
        self.set_model(model)

        if App.treeview.subpage == RowType.SERVER_BROWSER:
            call_out("start_cooldown", "", "")

        """
        There may be scenarios where opposed filter results
        deterministically yield 0 hits. The model needs to be
        emptied without triggering a fetch error. This method is
        reserved for cases where the query actually failed.
        """
        if not ModelManager.get_success():
            if self.wait_dialog:
                self.wait_dialog.destroy()
            spawn_dialog(api_warn_msg, Popup.RETURN)
            unblock_signals()
            return

        if App.right_panel.filters_vbox.get_active_combo() < 0:
            App.right_panel.filters_vbox.set_active_combo(0)
        App.grid.right_panel.filters_vbox.set_visible(True)
        for column in self.get_columns():
            column.connect("notify::width", self._on_col_width_changed)

        App.grid.statusbar.update_server_meta()

        if self.wait_dialog:
            self.wait_dialog.destroy()
        unblock_signals()
        self.grab_focus()
        App.treeview.select_first_row()

    def filter(self, mode: FilterMode, *args) -> None:
        block_signals()
        self.wait_dialog = GenericDialog("Filtering servers", Popup.WAIT)
        self.wait_dialog.show_all()

        ModelManager.set_store(App.treeview.get_model())
        App.treeview.set_model(None)

        thread = threading.Thread(
            target=ModelManager.filter, args=(mode, *args)
        )
        thread.start()

    def _background_quad(self, dialog: "GenericDialog", mode: RowType) -> None:
        # currently only used by list mods method
        def load():
            dialog.destroy()
            # suppress button panel if store is empty
            if total_mods == 0:
                grid.sel_panel.set_visible(False)
                right_panel.filters_vbox.set_visible(False)
                logger.info("Nothing to do, spawning notice dialog")
                spawn_dialog(data.stdout, Popup.RETURN)
                return
            else:
                grid.sel_panel.set_visible(True)
                grid.sel_panel.initialize()

            self.set_model(mod_store)
            self.grab_focus()
            size = locale.format_string("%.3f", total_size, grouping=True)
            pretty = pluralize("mods", total_mods)
            grid.statusbar.set_text(
                f"Found {total_mods:n} {pretty} taking up {size} MiB"
            )
            self.focus_first_row()

        grid = App.grid
        right_panel = grid.right_panel
        data = call_out(mode.dict["label"], "")

        # suppress errors if no mods available on system
        if data.returncode == 1:
            logger.info("Failed to find mods on local system")
            total_mods = 0
            total_size = 0
        else:
            if App.treeview.view == WindowContext.TABLE_MODS:
                grid.sel_panel.set_visible(True)
            result = self._parse_mod_rows(data)
            try:
                total_size = result[0]
                total_mods = result[1]
                info = (
                    f"Found mods on local system: "
                    f"{total_mods} total, occupies {total_size}"
                )
            except IndexError:
                total_size = 0
                total_mods = 0
                info = "Found mods on system, but was unable to parse results."
            finally:
                logger.info(info)
        GLib.idle_add(load)

    def _parse_log_rows(self, data: subprocess.CompletedProcess) -> bool:
        lines = data.stdout.splitlines()
        reader = csv.reader(lines, delimiter=delimiter)
        try:
            rows = [[row[0], row[1], row[2], row[3]] for row in reader if row]
        except IndexError:
            return False
        for row in rows:
            log_store.append(row)
        return True

    def _parse_mod_rows(self, data: subprocess.CompletedProcess) -> list:
        # GTK pads trailing zeroes on floats
        # https://stackoverflow.com/questions/26827434/gtk-cellrenderertext-with-format
        total = float(0)
        lines = data.stdout.splitlines()
        hits = len(lines)
        reader = csv.reader(lines, delimiter=delimiter)

        # Nonetype inherits default GTK color
        try:
            rows = [
                [row[0], row[1], row[2], locale.atof(row[3], func=float), None]
                for row in reader
                if row
            ]
        except IndexError:
            return []
        for row in rows:
            mod_store.append(row)
            total += float(row[3])
        return [total, hits]

    def _on_col_width_changed(
        self, col: Gtk.TreeViewColumn, width: GObject.ParamSpecInt
    ) -> None:
        def write_json(title, size):
            data = {"cols": {title: size}}
            j = json.dumps(data, indent=2)
            with open(geometry_path, "w") as outfile:
                outfile.write(j)
            logger.info(f"Wrote initial column widths to '{geometry_path}'")

        title = col.get_title()
        size = col.get_width()

        if os.path.isfile(geometry_path):
            with open(geometry_path, "r") as infile:
                try:
                    data = json.load(infile)
                    data["cols"][title] = size
                    with open(geometry_path, "w") as outfile:
                        outfile.write(json.dumps(data, indent=2))
                except json.decoder.JSONDecodeError:
                    logger.critical(f"JSON decode error in '{geometry_path}'")
                    write_json(title, size)
        else:
            write_json(title, size)

    def initialize_columns(self) -> None:
        if os.path.isfile(geometry_path):
            with open(geometry_path, "r") as infile:
                try:
                    data = json.load(infile)
                    valid_json = True
                except json.decoder.JSONDecodeError:
                    logger.critical(f"JSON decode error in '{geometry_path}'")
                    valid_json = False
        else:
            valid_json = False

        browser_cols = [
            "Name",
            "Map",
            "Perspective",
            "Gametime",
            "Players",
            "Maximum",
            "Queue",
            "IP",
            "Qport",
            "Ping",
        ]
        for i, column_title in enumerate(browser_cols):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_resizable(True)
            column.set_sort_column_id(i)

            if valid_json:
                try:
                    saved_size = data["cols"][column_title]
                except KeyError:
                    saved_size = 100
                column.set_fixed_width(saved_size)
                column.set_expand(True)
            else:
                if column_title == "Name":
                    column.set_fixed_width(800)
                if column_title == "Map":
                    column.set_fixed_width(300)

            self.append_column(column)

    @update_window_labels
    def _update_multi_column(self, mode: RowType, port: int = 27016) -> None:
        self.subpage = mode

        self.set_headers_visible(True)
        for column in self.get_columns():
            self.remove_column(column)
        row_store.clear()
        self.initialize_columns()
        self.set_selection_mode(Gtk.SelectionMode.SINGLE)

        self.wait_dialog = GenericDialog(
            "Fetching server metadata", Popup.WAIT
        )
        self.wait_dialog.show_all()
        thread = threading.Thread(
            target=self._query_servers, args=(mode, port)
        )
        thread.start()

    def _format_float(
        self,
        column: Gtk.TreeViewColumn,
        cell: Gtk.CellRendererText,
        model: Gtk.TreeModel,
        it: Gtk.TreeIter,
        data: Any,
    ) -> Any:
        # https://docs.huihoo.com/pygtk/2.0-tutorial/sec-CellRenderers.html
        val = model[it][3]
        formatted = locale.format_string("%.3f", val, grouping=True)
        cell.set_property("text", formatted)
        return

    def set_selection_mode(self, mode: Gtk.SelectionMode) -> None:
        sel = self.get_selection()
        sel.set_mode(mode)

    def _set_quad_col_mode(self, mode: RowType) -> None:
        mod_cols = ["Mod", "Symlink", "Dir", "Size (MiB)", "Color"]
        log_cols = ["Timestamp", "Flag", "Traceback", "Message"]
        match mode:
            case RowType.LIST_MODS:
                cols = mod_cols
                model = mod_store
                self.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
            case RowType.SHOW_LOG:
                cols = log_cols
                model = log_store
        self.set_model(model)

        for i, column_title in enumerate(cols):
            renderer = Gtk.CellRendererText()
            if mode == RowType.LIST_MODS:
                column = Gtk.TreeViewColumn(
                    column_title, renderer, text=i, foreground=4
                )
                if i == 3:
                    column.set_cell_data_func(
                        renderer, self._format_float, func_data=None
                    )
                if column_title == "Mod":
                    column.set_fixed_width(500)
                else:
                    column.set_fixed_width(150)
            else:
                # WindowContext.TABLE_LOG uses undecorated columns
                column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_sort_column_id(i)
            # hidden color property column
            if i != 4:
                self.append_column(column)

    @update_window_labels
    def _populate(self, context: WindowContext) -> None:
        self.view = context
        self.page = context
        self.subpage = None

        row_store.clear()
        array = context.dict["rows"]

        for item in array:
            label = item.dict["label"]
            row = (label,)
            row_store.append(row)
        App.grid.statusbar.refresh()
        App.grid.notebook.set_page_by_enum(NotebookPage.MAIN)
        self.grab_focus()

    @signal_emission
    def update_single_column(self, button_context: ButtonType) -> None:
        msg = (
            f"Returning from multi-column view to monocolumn view "
            f"for the context '{button_context}'"
        )
        logger.info(msg)
        model = self.get_model()
        if model:
            model.clear()
        ModelManager.wipe_cache(full=True)

        App.right_panel.enable_ping_button(False)
        App.right_panel.filters_vbox.reinit_panel()
        self.set_selection_mode(Gtk.SelectionMode.SINGLE)

        for column in self.get_columns():
            self.remove_column(column)
        for i, column_title in enumerate([button_context.dict["label"]]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            self.append_column(column)

        self.set_headers_visible(False)
        self.set_model(row_store)
        self._populate(button_context.dict["opens"])
        self.grab_focus()

    def update_quad_column(self, mode: RowType) -> None:
        for column in self.get_columns():
            self.remove_column(column)

        self.subpage = mode
        self.set_headers_visible(True)
        self._set_quad_col_mode(mode)

        mod_store.clear()
        log_store.clear()

        if mode == RowType.SHOW_LOG:
            data = call_out("show_log")
            res = self._parse_log_rows(data)
            App.treeview.focus_first_row()
            if not res:
                spawn_dialog(
                    "Failed to load log file, possibly corrupted", Popup.NOTIFY
                )
            return
        else:
            wait_dialog = GenericDialog("Checking mods", Popup.WAIT)
            wait_dialog.show_all()
            thread = threading.Thread(
                target=self._background_quad, args=(wait_dialog, mode)
            )
            thread.start()

    def dialog_hide(self) -> None:
        if hasattr(self, "wait_dialog"):
            self.wait_dialog.destroy()

    def dialog_show(self, msg: str) -> None:
        if hasattr(self, "wait_dialog"):
            self.wait_dialog.destroy()
        self.wait_dialog = GenericDialog(msg, Popup.WAIT)
        self.wait_dialog.show_all()

    def is_row_to_server_context(self, view: RowType) -> bool:
        """Row activation that jumps into a server table"""
        row_contexts = [
            RowType.SERVER_BROWSER,
            RowType.RECENT_SERVERS,
            RowType.SAVED_SERVERS,
        ]
        if view in row_contexts:
            return True
        return False

    def is_server_context(self, view: WindowContext) -> bool:
        """Server tables"""
        server_contexts = [
            WindowContext.TABLE_API,
            WindowContext.TABLE_SERVER,
        ]
        if view in server_contexts:
            return True
        return False

    def is_dynamic_context(self, view: WindowContext) -> bool:
        """Tables populated with arbitrary content"""
        dynamic_contexts = [
            WindowContext.TABLE_LOG,
            WindowContext.TABLE_SERVER,
            WindowContext.TABLE_API,
        ]
        if view in dynamic_contexts:
            return True
        return False

    def set_view(self, view):
        self.view = view

    def get_view(self):
        return self.view

    def prepare_connection(
        self, record: Record
    ) -> subprocess.CompletedProcess | None:
        """
        Always called on a thread with a dialog on the transient parent window
        """
        prereqs = Servers.get_prereqs(record.ip, record.qport)
        if prereqs.appid is None:
            logger.warning(f"Query to '{record.ip}:{record.qport}' timed out")
            msg = "Timed out when querying server, check IP or try again later"
            spawn_dialog(msg, Popup.NOTIFY)
            return None

        build = "DayZ" if prereqs.appid == APPID_DAYZ else "DayZ Experimental"
        steam_path = query_config("default_steam_path")[0]

        if len(steam_path) < 1:
            logger.critical(
                "Config file has no value set for 'default_steam_path'"
            )
            msg = f"Local Steam installation is not set, possibly malformed config file."
            spawn_dialog(msg, Popup.NOTIFY)
            return None

        try:
            pefile_path = PeFile.get_pefile_path(steam_path, prereqs.appid)
        except AppNotInstalledError:
            logger.critical(
                f"'{prereqs.appid}' not found in user's libraryfolders"
            )
            msg = (
                f"This server is running {build}. You can install "
                f"{build} by searching for it in your Steam library. "
                f"If you recently installed {build} or moved it to a different drive, "
                "restart Steam to allow these changes to synchronize, then try again."
            )
            spawn_dialog(msg, Popup.NOTIFY)
            return None
        except AppMovedError:
            logger.critical(
                f"Library folder synch error for '{prereqs.appid}'"
            )
            msg = (
                f"Steam is reporting that {build} is installed at a non-existent location. "
                f"If you recently installed {build} or moved it to a different drive, "
                "restart Steam to allow these changes to synchronize, then try again."
            )
            spawn_dialog(msg, Popup.NOTIFY)
            return None
        except (VDFLoadError, PeFileError, Exception) as e:
            logger.critical(e)
            msg = "Steam settings or DayZ installation may be corrupted. Try restarting Steam."
            spawn_dialog(msg, Popup.NOTIFY)
            return None

        try:
            local_vers = PeFile.get_dayz_version(pefile_path)
        except (PeFileError, Exception) as e:
            """
            Currently permissive; file exists, but was unparseable.
            """
            logger.warning(f"Failed to parse PE file: {e}")
            local_vers = None

        try:
            remote_vers = PeFile.dayz_version_from_str(prereqs.version)
        except Exception:
            remote_vers = None

        if local_vers is not None and remote_vers is not None:
            match = PeFile.compare_versions(local_vers, remote_vers)

            match match:
                case VersionMatch.LOCAL_OLDER:
                    msg = (
                        f"This server is running a newer build ({prereqs.version}) of {build} than "
                        f"your local version. You may be unable to connect. Proceed anyway?"
                    )
                    res = spawn_dialog(msg, Popup.CONFIRM)
                    if res is True:
                        return None
                case VersionMatch.LOCAL_NEWER:
                    msg = (
                        f"This server is running an out-of-date build ({prereqs.version}) of {build}. "
                        "You may be unable to connect. Proceed anyway?"
                    )
                    res = spawn_dialog(msg, Popup.CONFIRM)
                    if res is True:
                        return None
                case VersionMatch.SAME_VERSION:
                    pass

        if prereqs.password is True:
            msg = (
                "This server is password-protected and you will be "
                "prompted when connecting. Do you want to proceed?"
            )
            res = spawn_dialog(msg, Popup.CONFIRM)
            if res is True:
                return None

        """
        When using RowType.CONN_BY_IP, the gameport needs to be interpolated
        """
        record.gameport = prereqs.gameport
        addr = record_to_str(record)
        proc = call_out(
            "try_connect", addr, str(prereqs.appid), str(pefile_path)
        )
        return proc

    @signal_emission
    @update_window_labels
    def _on_row_activated(
        self,
        treeview: Gtk.TreeView,
        tree_iter: Gtk.TreePath,
        col: Gtk.TreeViewColumn,
    ) -> None:

        context = self.page
        chosen_row = self.get_value_at_index(0)

        if self.view == WindowContext.TABLE_MODS:
            self.open_workshop()
            return

        if self.is_dynamic_context(self.view):
            cr = RowType.DYNAMIC
        else:
            cr = RowType.str2rowtype(chosen_row)
            wc = WindowContext.row2con(cr)
            self.set_view(wc)

        output = cr
        logger.info(f"User selected '{cr}' for the context '{context}'")

        if cr == RowType.SCAN_LAN:
            lan_dialog = LanDialog()
            lan_dialog.run()
            lan_dialog.destroy()
            port = lan_dialog.get_selected_port()
            if port is None:
                return
            App.right_panel.filters_vbox.enable_all_filters()
            self._update_multi_column(cr, port=port)
            return

        if self.is_row_to_server_context(cr):
            if cr == RowType.SERVER_BROWSER:
                cooldown = call_out("test_cooldown", "", "")
                if cooldown.returncode == 1:
                    spawn_dialog(cooldown.stdout, Popup.NOTIFY)
                    self.set_view(WindowContext.MAIN_MENU)
                    return
                try:
                    key = query_config("steam_api")[0]
                except IndexError:
                    spawn_dialog("No Steam API key is set.", Popup.NOTIFY)
                    self.set_view(WindowContext.MAIN_MENU)
                    return
                if len(key) < 1:
                    spawn_dialog("No Steam API key is set.", Popup.NOTIFY)
                    self.set_view(WindowContext.MAIN_MENU)
                    return
                App.grid.right_panel.filters_vbox.reinit_filters()
            else:
                # local server lists need not be filter-restricted
                App.right_panel.filters_vbox.enable_all_filters()
            self._update_multi_column(cr)
            return

        match self.view:
            case WindowContext.TABLE_MODS | WindowContext.TABLE_LOG:
                self.update_quad_column(cr)
            case WindowContext.TABLE_SERVER | WindowContext.TABLE_API:
                record = self.get_record_dict()
                if record is None:
                    return
                thread_new_with_dialog(
                    self.prepare_connection,
                    parse_shell_output,
                    "Querying server",
                    None,
                    [record],
                )
            case _:  # any other non-server option from the main menu
                process_tree_option(output)


class AppHeaderBar(Gtk.HeaderBar):
    def __init__(self):
        super().__init__()
        self.props.title = app_name
        self.set_decoration_layout(":minimize,maximize,close")
        self.set_show_close_button(True)


class GenericDialog(Gtk.MessageDialog):
    def __init__(self, text: str, mode: Popup):
        match mode:
            case Popup.WAIT:
                dialog_type = Gtk.MessageType.INFO
                button_type = Gtk.ButtonsType.NONE
                header_text = "Please wait"
            case Popup.NOTIFY | Popup.RETURN | Popup.QUIT:
                dialog_type = Gtk.MessageType.INFO
                button_type = Gtk.ButtonsType.OK
                header_text = "Notice"
            case Popup.CONFIRM:
                dialog_type = Gtk.MessageType.QUESTION
                button_type = Gtk.ButtonsType.OK_CANCEL
                header_text = "Confirmation"
            case Popup.ENTRY:
                dialog_type = Gtk.MessageType.QUESTION
                button_type = Gtk.ButtonsType.OK_CANCEL
                header_text = "User input required"
            case Popup.MODLIST:
                dialog_type = Gtk.MessageType.INFO
                button_type = Gtk.ButtonsType.OK
                header_text = "Modlist"
            case Popup.DETAILS:
                dialog_type = Gtk.MessageType.INFO
                button_type = Gtk.ButtonsType.OK
                header_text = "Server details"

        # steam deck prints <2> if dialog title is duplicated
        Gtk.MessageDialog.__init__(
            self,
            transient_for=App.window,
            message_type=dialog_type,
            text=header_text,
            secondary_text=textwrap.fill(text, 50),
            buttons=button_type,
            title=f"{app_name} - Dialog",
            modal=True,
        )

        if mode == Popup.WAIT:
            dialogBox = self.get_content_area()
            spinner = Gtk.Spinner()
            dialogBox.pack_end(spinner, False, False, 0)
            spinner.start()
            self.connect("delete-event", self._on_dialog_delete)

        if mode == Popup.RETURN:
            button_label = "Return to main menu"
            ok = self.action_area.get_children()[0]
            ok.set_label(button_label)
            ok.connect("clicked", self._return_to_main_menu)
            self.connect("delete-event", self._return_to_main_menu)

        if mode == Popup.QUIT:
            button_label = "Exit"
            ok = self.action_area.get_children()[0]
            ok.set_label(button_label)
            ok.connect("clicked", save_res_and_quit)
            self.connect("delete-event", save_res_and_quit)

        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(500, 0)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.action_area.set_layout(Gtk.ButtonBoxStyle.CENTER)
        self.action_area.set_margin_bottom(20)
        self.outer = self.get_content_area()
        self.outer.set_margin_start(30)
        self.outer.set_margin_end(30)

    def _on_dialog_delete(
        self, response_id: Gtk.ResponseType
    ) -> Literal[True]:
        return True

    def _return_to_main_menu(self, widget: Gtk.Widget) -> None:
        App.treeview.update_single_column(ButtonType.MAIN_MENU)

    def update_label(self, text: str) -> None:
        self.format_secondary_text(text)


class LanDialog(Gtk.MessageDialog):
    """
    Performs integer validation on the provided port
    and blocks if out of range. Returns None if user cancels
    """

    def __init__(self):
        super().__init__(
            transient_for=App.window,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Scan LAN servers",
            secondary_text="Select the query port",
            title="{appname}",
            modal=True,
        )

        self.set_size_request(500, 0)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        buttons = [
            ("Use default query port (27016)", Port.DEFAULT),
            ("Enter custom query port", Port.CUSTOM),
        ]

        self.button_box = Gtk.Box()
        self.button_box.set_orientation(Gtk.Orientation.VERTICAL)
        self.button_box.active_button = None

        for k, v in buttons:
            button = Gtk.RadioButton(label=k)
            button.port = v
            button.connect("toggled", self._on_button_toggled)
            self.button_box.add(button)
            if v == Port.DEFAULT:
                self.button_box.active_button = button
            else:
                button.join_group(self.button_box.active_button)

        self.entry = Gtk.Entry()
        self.button_box.add(self.entry)
        self.entry.set_no_show_all(True)

        self.warn_label = Gtk.Label(label="Invalid port")
        self.warn_label.set_no_show_all(True)
        self.button_box.add(self.warn_label)

        content = self.get_content_area()
        content.pack_start(self.button_box, False, False, 0)
        content.set_margin_start(30)
        content.set_margin_end(30)
        content.show_all()

        self.action_area.set_layout(Gtk.ButtonBoxStyle.CENTER)
        self.action_area.set_margin_bottom(20)

        self.port = None
        self.ok = self.action_area.get_children()[1]

        self.connect("response", self._on_dialog_response)
        self.connect("key-press-event", self._on_keypress)
        self.connect("delete-event", self.restore_context)

        self.entry.connect("insert-text", self._on_text_typed)
        self.entry.get_property("buffer").connect(
            "deleted-text", self._on_text_deleted
        )

    def _validate(self, text: str) -> None:
        if self._is_invalid(text):
            state = False
            self.warn_label.set_visible(True)
        else:
            state = True
            self.warn_label.set_visible(False)

        self.ok.set_sensitive(state)
        if len(text) == 0:
            self.warn_label.set_visible(False)

    def _on_text_deleted(
        self, buffer: Gtk.EntryBuffer, position: int, chars: int
    ) -> None:
        text = buffer.get_text()
        self._validate(text)

    def _on_text_typed(
        self, entry: Gtk.Entry, text: str, length: int, pos: int
    ) -> None:
        self._validate(entry.get_text() + text)

    def restore_context(self, *args) -> None:
        context = WindowContext.MAIN_MENU
        App.treeview.set_view(context)

    def _on_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Return:
            if self.ok.is_sensitive():
                self.response(Gtk.ResponseType.OK)
            if self.button_box.get_children()[0].is_focus():
                self.response(Gtk.ResponseType.OK)
            else:
                self.restore_context()

        if event.keyval == Gdk.KEY_Up:
            self.ok.set_sensitive(True)
            self.entry.set_text("")
            self.button_box.get_children()[0].grab_focus()

    def _on_dialog_response(
        self, dialog: "LanDialog", response: Gtk.ResponseType
    ) -> None:
        cancel_events = [
            Gtk.ResponseType.CLOSE,
            Gtk.ResponseType.CANCEL,
            Gtk.ResponseType.DELETE_EVENT,
        ]

        if response in cancel_events:
            self.restore_context()
            return

        string = self.entry.get_text()
        port = self.button_box.active_button.port

        match port:
            case Port.DEFAULT:
                self.port = 27016
            case Port.CUSTOM:
                if self._is_invalid(string):
                    self.stop_emission_by_name("response")
                else:
                    self.port = int(string)

    def _is_invalid(self, string: str) -> bool:
        if (
            not string.isdigit()
            or int(string) == 0
            or int(string[0]) == 0
            or int(string) > 65535
        ):
            return True
        return False

    def get_selected_port(self) -> int:
        return self.port

    def _on_button_toggled(self, button: Gtk.Button) -> None:
        if button.get_active():
            self.button_box.active_button = button
            match button.port:
                case Port.DEFAULT:
                    self.entry.set_visible(False)
                case Port.CUSTOM:
                    self.entry.set_visible(True)
                    self.entry.grab_focus()
                    self.ok.set_sensitive(False)


class DetailsDialog(GenericDialog):
    def __init__(self, server_name: str, ip: str, qport: int):
        super().__init__(server_name, Popup.DETAILS)

        dialog_box = self.get_content_area()
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(800, 700)

        self.ip = ip.split(":")[0]
        self.qport = qport
        self.store = Gtk.ListStore(str, str, Pango.Weight)

        self.view = Gtk.TreeView(
            enable_search=False,
            search_column=-1,
            headers_visible=False,
            fixed_height_mode=True,
        )
        self.view.connect("row-activated", self._on_row_activated)

        for i, column_title in enumerate(["Item", "Details"]):
            renderer = Gtk.CellRendererText(xalign=0)
            if i == 0:
                column = Gtk.TreeViewColumn(
                    column_title, renderer, text=i, weight=2
                )
            else:
                column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            if i != 2:
                self.view.append_column(column)
            column.set_sort_column_id(i)
            column.set_expand(True)

        scrollable_tree = Gtk.ScrolledWindow()
        scrollable_tree.add(self.view)
        scrollable_tree.set_size_request(700, 200)

        scrollable_message = Gtk.ScrolledWindow()
        desc = Gtk.Label(label="Server message", valign=Gtk.Align.START)
        add_class(desc, "details-heading")
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER
        )
        self.description = Gtk.Label(
            justify=Gtk.Justification.CENTER, wrap=True
        )
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_bottom(10)
        for el in desc, sep, self.description:
            box.add(el)
        scrollable_message.add(box)

        dialog_box.pack_start(scrollable_tree, True, True, 0)
        dialog_box.pack_start(scrollable_message, True, True, 0)

        self.wait_dialog = GenericDialog("Fetching details", Popup.WAIT)
        self.wait_dialog.show_all()
        thread = threading.Thread(
            target=self._background, args=(self.wait_dialog, ip, qport)
        )
        thread.start()

    def _on_row_activated(
        self,
        treeview: Gtk.TreeView,
        tree_iter: Gtk.TreeIter,
        col: Gtk.TreeViewColumn,
    ) -> None:
        self.destroy()

    def _load(self) -> None:
        if self.wait_dialog:
            self.wait_dialog.destroy()
        if self.success is False:
            msg = """Error while contacting server, possibly timed out.
            Please wait and try again.
            """
            spawn_dialog(msg, Popup.NOTIFY)
            return
        self.show_all()
        self.run()
        self.destroy()

    def _background(
        self, dialog: "GenericDialog", ip: str, qport: int
    ) -> None:
        response = Servers.details(self.ip, self.qport)
        if response.success:
            for row in response.data:
                self.store.append(row + [Pango.Weight.BOLD])
            self.view.set_model(self.store)

            text = response.description
            reg = r"\s(www\.*?)"
            text = re.sub(reg, " http://" + r"\1", text)
            reg2 = r"(http.*?)([ ,\r\n]|$)"
            text = re.sub(reg2, comp(r"\1") + r"\2", text)

            self.description.set_markup(text)
        self.success = response.success
        GLib.idle_add(self._load)


def comp(string):
    return f'<a href="{string}">{string}</a>'


class ModDialog(GenericDialog):
    def __init__(self, record: str):
        msg = "Enter/double click a row to open in Steam Workshop."
        super().__init__(textwrap.dedent(msg), Popup.MODLIST)

        dialogBox = self.get_content_area()
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(800, 500)

        self.scrollable = Gtk.ScrolledWindow()
        self.view = Gtk.TreeView(
            enable_search=False, search_column=-1, fixed_height_mode=True
        )
        self.scrollable.add(self.view)
        set_surrounding_margins(self.scrollable, 20)

        self.view.connect("row-activated", self._on_row_activated)

        for i, column_title in enumerate(["Mod", "ID", "Installed"]):
            renderer = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            self.view.append_column(column)
            column.set_sort_column_id(i)
            match column_title:
                case "Mod":
                    column.set_fixed_width(350)
                case "ID":
                    column.set_fixed_width(200)
                case _:
                    pass
        dialogBox.pack_end(self.scrollable, True, True, 0)

        wait_dialog = GenericDialog("Fetching modlist", Popup.WAIT)
        wait_dialog.show_all()
        thread = threading.Thread(
            target=self._background, args=(wait_dialog, record)
        )
        thread.start()

    def _background(self, dialog: "GenericDialog", record: str) -> None:
        def _load():
            dialog.destroy()
            if data.returncode == 1:
                msg = """Error while contacting server, possibly timed out.
                Please wait and try again.
                """
                spawn_dialog(msg, Popup.NOTIFY)
                return
            self.show_all()
            self.set_markup(f"Modlist ({mod_count} mods)")
            self.run()
            self.destroy()

        record = App.treeview.get_record_dict()
        if not record:
            return
        data = call_out("show_server_modlist", record.ip, str(record.qport))
        mod_count = self._parse_modlist_rows(data)
        self.view.set_model(modlist_store)
        GLib.idle_add(_load)

    def _parse_modlist_rows(
        self, data: subprocess.CompletedProcess
    ) -> bool | int:
        lines = data.stdout.splitlines()
        hits = len(lines)
        reader = csv.reader(lines, delimiter=delimiter)
        try:
            rows = [[row[0], row[1], row[2]] for row in reader if row]
        except IndexError:
            return 1
        for row in rows:
            modlist_store.append(row)
        return hits

    def _on_row_activated(
        self,
        treeview: Gtk.TreeView,
        tree_iter: Gtk.TreeIter,
        col: Gtk.TreeViewColumn,
    ) -> None:
        select = treeview.get_selection()
        sels = select.get_selected_rows()
        (model, pathlist) = sels
        if len(pathlist) < 1:
            return
        path = pathlist[0]
        tree_iter = model.get_iter(path)
        mod_id = model.get_value(tree_iter, 1)
        call_bash_func("open_workshop_page", mod_id)


class LinkDialog(GenericDialog):
    def __init__(
        self, text: str, link: str | None, command: RowType, uid: str = ""
    ):
        super().__init__(text, Popup.NOTIFY)

        text = textwrap.dedent(text)
        self.dialogBox = self.get_content_area()
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(500, 0)

        if link:
            button = Gtk.Button(label=link)
            button.set_margin_start(60)
            button.set_margin_end(60)
            button.connect("clicked", self._on_button_clicked, uid)
            self.dialogBox.pack_end(button, False, False, 0)

        self.show_all()
        self.connect("response", self._on_dialog_response, command)

    def _on_button_clicked(self, button: Gtk.Button, uid: str) -> None:
        call_bash_func("open_user_workshop", uid)

    def _on_dialog_response(
        self, dialog: "LinkDialog", resp: Gtk.ResponseType, command: RowType
    ) -> None:
        match resp:
            case Gtk.ResponseType.DELETE_EVENT:
                return
            case Gtk.ResponseType.OK:
                self.destroy()
                call_out("toggle", command.dict["label"])
                App.grid.statusbar.refresh()


class EntryDialog(GenericDialog):
    def __init__(self, text: str, mode: Popup, link: str):
        super().__init__(text, mode)

        """
        Returns user input as a string or None
        """

        self.dialog = GenericDialog(text, mode)
        self.dialogBox = self.dialog.get_content_area()
        self.dialog.set_default_response(Gtk.ResponseType.OK)
        self.dialog.set_size_request(500, 0)

        self.userEntry = Gtk.Entry()
        set_surrounding_margins(self.userEntry, 20)
        self.userEntry.set_margin_top(0)
        self.userEntry.set_size_request(250, 0)
        self.userEntry.set_activates_default(True)
        self.dialogBox.pack_start(self.userEntry, False, False, 0)

        if link:
            button = Gtk.Button(label=link)
            button.set_margin_start(60)
            button.set_margin_end(60)
            button.connect("clicked", self._on_button_clicked)
            self.dialogBox.pack_end(button, False, False, 0)

        self.ok = self.dialog.action_area.get_children()[1]
        self.ok.set_sensitive(False)
        self.userEntry.connect("insert-text", self._on_text_typed)
        self.userEntry.get_property("buffer").connect(
            "deleted-text", self._on_text_deleted
        )

    def _is_valid_text(self, text: str) -> bool:
        if text.isspace():
            return False
        if len(text) == 0:
            return False
        return True

    def _on_text_deleted(
        self, buffer: Gtk.EntryBuffer, position: int, chars: int
    ) -> None:
        text = buffer.get_text()
        state = self._is_valid_text(text)
        self.ok.set_sensitive(state)

    def _on_text_typed(
        self, entry: Gtk.Entry, text: str, length: int, pos: int
    ) -> None:
        state = self._is_valid_text(text)
        self.ok.set_sensitive(state)

    def _on_button_clicked(self, button: Gtk.Button) -> None:
        label = button.get_label()
        call_bash_func("Open link", label)

    def get_input(self) -> str | None:
        self.dialog.show_all()

        response = self.dialog.run()
        text = self.userEntry.get_text()
        self.dialog.destroy()
        if (response == Gtk.ResponseType.OK) and (text != ""):
            return text
        else:
            return None


class ScrollableNote(Gtk.Box):
    def __init__(self, content_box: Gtk.Box, back_button=True):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.scrollable = Gtk.ScrolledWindow()
        self.scrollable.set_vexpand(True)

        self.back_button = Gtk.Button(
            label="Back", hexpand=True, halign=Gtk.Align.CENTER
        )

        self.gutter = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, valign=Gtk.Align.END
        )
        if back_button:
            self.gutter.add(self.back_button)
            self.back_button.connect("clicked", self._on_back_clicked)

        self.scrollable.add(content_box)
        self.add(self.scrollable)
        self.add(self.gutter)

    @update_window_labels
    def _on_back_clicked(self, button: Gtk.Button) -> None:
        App.notebook.return_prior()


class InfoEventBox(Gtk.EventBox):
    def __init__(self, text: str):
        super().__init__(margin_start=10)

        self.text = text

        self.icon = Gtk.Image.new_from_icon_name(
            "help-about-symbolic", Gtk.IconSize.LARGE_TOOLBAR
        )
        self.icon.set_opacity(0.8)
        box = Gtk.Box()
        box.add(self.icon)

        self.connect("enter-notify-event", self._on_enter_tooltip)
        self.connect("leave-notify-event", self._on_leave_tooltip)
        self.add(box)

    def _on_enter_tooltip(
        self, eventbox: Gtk.EventBox, eventcrossing: Gdk.EventCrossing
    ) -> None:
        self.icon.set_opacity(1)
        App.grid.statusbar.set_text(self.text)

    def _on_leave_tooltip(
        self, eventbox: Gtk.EventBox, eventcrossing: Gdk.EventCrossing
    ) -> None:
        self.icon.set_opacity(0.8)
        App.grid.statusbar.set_text("")


class LeftLabel(Gtk.Label):
    def __init__(self, text: str, tooltip: str = ""):
        super().__init__(
            label=text,
            halign=Gtk.Align.START,
        )
        self.set_tooltip_text(tooltip)
        pass


class Options(Gtk.Box):
    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            margin_start=10,
            margin_end=10,
        )

        self.DEFAULT_WIDTH = 1
        self.DEFAULT_HEIGHT = 1

        label = Gtk.Label(label="Options")
        label.set_halign(Gtk.Align.CENTER)
        add_class(label, "page-heading")
        self.add(label)

        self.steam_entry = None
        self.bm_entry = None

        self.steam_box = self._make_submit_field(
            "Enter your Steam API key", Preferences.STEAM, True
        )
        self.bm_box = self._make_submit_field(
            "Enter your Battlemetrics API key", Preferences.BM, True
        )
        api_rows = [
            [LeftLabel("Steam API key"), self.steam_box],
            [LeftLabel("Battlemetrics API key"), self.bm_box],
        ]

        self.player_box = self._make_submit_field(
            "Identifies you to other players in-game", Preferences.NAME
        )
        self.fullscreen_toggle = self.make_binary_radio(
            "Last used dimensions",
            "Always fullscreen",
            Preferences.WINDOW,
        )
        self.steam_toggle = self.make_binary_radio(
            "Steam", "Flatpak (experimental)", Preferences.CLIENT
        )

        pref_rows = [
            [LeftLabel("Steam client"), self.steam_toggle],
            [LeftLabel("Window size at boot"), self.fullscreen_toggle],
            [LeftLabel("Player name"), self.player_box],
        ]

        self.mod_install_toggle = self.make_binary_radio(
            "Manual", "Auto", Preferences.INSTALL
        )
        self.force_button = Gtk.Button(label="Update")
        self.force_button.connect("clicked", self._on_force_update_clicked)
        # sensitivity state is set after config file is loaded
        self.force_button.set_sensitive(False)

        msg = (
            "Manual: prompt to subscribe to mods in Steam. "
            "Auto: unmanned downloads."
        )
        eb = InfoEventBox(msg)

        msg = "Synchronize all local mods. Automatic mode must be enabled."
        eb2 = InfoEventBox(msg)

        mod_rows = [
            [LeftLabel("Mod install mode"), self.mod_install_toggle, eb],
            [LeftLabel("Force update local mods"), self.force_button, eb2],
        ]

        self.dayz_version_label = Gtk.Label(label="-")
        self.dayz_exp_version_label = Gtk.Label(label="-")

        self.branch_combo = Gtk.ComboBoxText()
        self.branch_combo.append_text("Stable")
        self.branch_combo.append_text("Testing")
        self.branch_combo.set_active(0)
        self.branch_combo.connect("changed", self._on_branch_changed)

        msg = (
            "Stable: only contains stable features. "
            "Testing: pre-release beta, contains new features."
        )
        eb = InfoEventBox(msg)

        version_rows = [
            [LeftLabel("DayZ"), self.dayz_version_label],
            [LeftLabel("DayZ Experimental"), self.dayz_exp_version_label],
            [LeftLabel("DZGUI branch"), self.branch_combo, eb],
        ]

        api_grid = self._make_grid(api_rows)
        prefs_grid = self._make_grid(pref_rows)
        mods_grid = self._make_grid(mod_rows)
        version_grid = self._make_grid(version_rows)

        col = 1
        row = 1
        grid = Gtk.Grid(
            orientation=Gtk.Orientation.VERTICAL,
            row_spacing=30,
            hexpand=True,
        )

        for frame in [
            self.make_frame(api_grid, "API Keys"),
            self.make_frame(prefs_grid, "Preferences"),
            self.make_frame(mods_grid, "Mods"),
            self.make_frame(version_grid, "Version"),
        ]:
            grid.attach(
                frame, col, row, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT
            )
            row += 1

        self.scrollable = Gtk.ScrolledWindow(vexpand=True)
        self.scrollable.add(grid)
        self.add(self.scrollable)

    def _make_submit_field(
        self,
        placeholder: str,
        context: Preferences,
        private: bool = False,
    ) -> Gtk.Box:

        entry = Gtk.Entry(placeholder_text=placeholder, hexpand=True)
        button = Gtk.Button(label="Save")

        entry.sibling = button
        entry.get_property("buffer").sibling = button

        button.connect("clicked", self._on_save_clicked, entry, context)
        entry.connect("insert-text", self._on_text_typed, context)
        entry.connect("activate", self._on_field_activated, context)
        entry.get_property("buffer").connect(
            "deleted-text", self._on_text_deleted, context
        )

        if private:
            entry.set_icon_from_icon_name(
                Gtk.EntryIconPosition.SECONDARY, "view-reveal-symbolic"
            )
            entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
            entry.connect("icon-release", self._on_icon_release)
            entry.set_visibility(False)

            if context == Preferences.STEAM:
                self.steam_entry = entry
            else:
                self.bm_entry = entry

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.add(entry)
        box.add(button)

        return box

    def _on_field_activated(
        self, entry: Gtk.Entry, context: Preferences
    ) -> None:
        text = entry.get_text()
        button = entry.sibling
        if not self._is_valid_text(text, context):
            return
        self._on_save_clicked(button, entry, context)

    def _make_grid(self, rows: list) -> Gtk.Grid:
        grid = Gtk.Grid(
            orientation=Gtk.Orientation.VERTICAL,
            column_spacing=10,
            row_spacing=5,
            margin_start=5,
            margin_end=5,
            margin_top=10,
            margin_bottom=10,
        )
        row = 1
        for record in rows:
            col = 1
            for el in record:
                grid.attach(
                    el, col, row, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT
                )
                col += 1
            row += 1
        return grid

    def _on_save_clicked(
        self, button: Gtk.Button, entry: Gtk.Entry, context: Preferences
    ) -> None:
        show_wait_dialog = True
        wait_msg = "Working"
        button.set_sensitive(False)
        match context:
            case Preferences.NAME:
                toggle = RowType.CHNG_PLAYER
                show_wait_dialog = False
                text = entry.get_text().strip()
            case Preferences.STEAM:
                toggle = RowType.CHNG_STEAM_API
                text = "".join(entry.get_text().split())
            case Preferences.BM:
                toggle = RowType.CHNG_BM_API
                text = "".join(entry.get_text().split())
        cmd_string = toggle.dict["label"]
        call_on_thread(show_wait_dialog, cmd_string, wait_msg, text)

    def revert(self, mode: Preferences) -> None:
        if mode == Preferences.STEAM:
            self.steam_entry.set_text(self.old_steam)
        else:
            self.bm_entry.set_text(self.old_bm)
        pass

    def _on_force_update_clicked(self, button: Gtk.Button) -> None:
        wait_msg = "Updating mods"
        cmd = "Force update local mods"
        show_wait_dialog = True
        call_on_thread(show_wait_dialog, cmd, wait_msg, "")

    def _on_branch_changed(self, combo: Gtk.ComboBoxText) -> None:
        # prevent triggering on initial init
        if App.treeview.subpage is not RowType.OPTIONS:
            return
        process_toggle(RowType.TGL_BRANCH)

    def _on_radio_toggled(
        self, button: Gtk.RadioButton, context: Preferences
    ) -> None:
        if App.treeview.subpage is None:
            return
        match context:
            case Preferences.CLIENT:
                toggle = RowType.TGL_STEAM
            case Preferences.INSTALL:
                toggle = RowType.TGL_INSTALL
                state = button.get_group()[0].get_active()
                self.force_button.set_sensitive(state)
            case Preferences.WINDOW:
                toggle = RowType.TGL_FULLSCREEN
        process_toggle(toggle)

    def _is_valid_text(self, text: str, context: Preferences) -> bool:
        if text.isspace():
            return False
        if len(text) == 0:
            return False

        match context:
            case Preferences.NAME:
                old = self.old_name
            case Preferences.STEAM:
                old = self.old_steam
            case Preferences.BM:
                old = self.old_bm
        if text == old:
            return False
        return True

    def _on_text_deleted(
        self,
        buffer: Gtk.EntryBuffer,
        position: int,
        chars: int,
        context: Preferences,
    ) -> None:

        text = buffer.get_text()
        state = self._is_valid_text(text, context)
        buffer.sibling.set_sensitive(state)

    def _on_text_typed(
        self,
        entry: Gtk.Entry,
        text: str,
        length: int,
        pos: int,
        context: Preferences,
    ) -> None:

        buffer = entry.get_property("buffer")
        text = buffer.get_text() + text
        state = self._is_valid_text(text, context)
        entry.sibling.set_sensitive(state)

    def make_binary_radio(
        self,
        first_option: str,
        second_option: str,
        context: Preferences,
    ) -> Gtk.Box:

        hbox = Gtk.Box(spacing=5, halign=Gtk.Align.START)
        radio1 = Gtk.RadioButton.new_with_label(None, first_option)
        radio2 = Gtk.RadioButton.new_from_widget(radio1)
        radio2.set_label(second_option)
        radio1.connect("toggled", self._on_radio_toggled, context)
        hbox.pack_start(radio1, False, False, 0)
        hbox.pack_start(radio2, False, False, 0)

        return hbox

    def make_frame(self, widget: Gtk.Widget, text: str) -> Gtk.Box:
        label = Gtk.Label(label=text)
        label.set_halign(Gtk.Align.START)
        add_class(label, "settings-subheading")

        frame = Gtk.Frame(hexpand=True)
        frame.add(widget)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add(label)
        box.add(frame)

        return box

    def populate_settings(self) -> None:
        if not os.path.isfile(config_file):
            msg = (
                "DZGUI configuration file not found. "
                "Please exit and restart to regenerate it."
            )
            spawn_dialog(msg, Popup.QUIT)
        config_vals.clear()
        for i in query_config():
            config_vals.append(i)

        branch = config_vals[0]
        install = config_vals[2]
        name = config_vals[3]
        client = config_vals[5]
        fullscreen = config_vals[6]
        default_steam_path = config_vals[7]

        try:
            steam = query_config("steam_api")[0]
            bm = query_config("api_key")[0]
        except IndexError:
            return

        self.old_steam = steam
        self.old_bm = bm
        self.old_name = name

        self.steam_entry.set_text(steam)
        self.bm_entry.set_text(bm)
        self.player_box.get_children()[0].set_text(name)

        if install == "1":
            radio = 1
            self.force_button.set_sensitive(True)
        else:
            radio = 0
        self.mod_install_toggle.get_children()[radio].set_active(True)

        if client == "flatpak":
            radio = 1
        else:
            radio = 0
        self.steam_toggle.get_children()[radio].set_active(True)

        if fullscreen == "true":
            radio = 1
        else:
            radio = 0
        self.fullscreen_toggle.get_children()[radio].set_active(True)

        for field in (
            [name, self.player_box],
            [steam, self.steam_box],
            [bm, self.bm_box],
        ):
            if field[0] == "":
                field[1].get_children()[1].set_sensitive(False)

        try:
            pe_file_path = PeFile.get_pefile_path(
                default_steam_path, APPID_DAYZ
            )
            vers = PeFile.get_dayz_version(pe_file_path)
            dayz_version = PeFile.dayz_version_to_str(vers)
        except Exception:
            dayz_version = "-"

        try:
            exp_file_path = PeFile.get_pefile_path(
                default_steam_path, APPID_DAYZ_EXP
            )
            vers = PeFile.get_dayz_version(exp_file_path)
            dayz_exp_version = PeFile.dayz_version_to_str(vers)
        except Exception:
            dayz_exp_version = "-"

        self.dayz_version_label.set_text(dayz_version)
        self.dayz_exp_version_label.set_text(dayz_exp_version)

        if branch == "testing":
            self.branch_combo.set_active(1)
        else:
            self.branch_combo.set_active(0)

    def _on_icon_release(
        self,
        widget: Gtk.Entry,
        icon_pos: Gtk.EntryIconPosition,
        event: Gdk.Event,
    ) -> None:
        visible = widget.get_visibility()
        if visible:
            icon = "view-reveal-symbolic"
            state = False
        else:
            icon = "view-conceal-symbolic"
            state = True
        widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)
        widget.set_visibility(state)


class KeybindingsDialog(Gtk.Box):
    """
    Notebook page holding a prearranged grid
    of keybindings and their descriptions
    """

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

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
            "Ctrl-p": "refresh ping",
            "Ctrl-f": "jump to keyword search field",
            "Ctrl-m": "jump to maps field",
            "Ctrl-d": "toggle dry run (debug) mode",
            "ESC": "return to table",
            "1-9": "toggle filter 1-9 on/off",
            "0": "toggle filter 10",
            "Minus": "toggle filter 11",
            "Backslash": "toggle filter 12",
        }
        vim = {
            "j": "Move down a row/scroll up",
            "k": "Move up a row/scroll down",
            "l": "Jump to main area from sidebar",
            "h": "Jump to sidebar from main area",
            "gg": "Jump to first row/top of page",
            "G": "Jump to last row/bottom of page",
        }

        label = Gtk.Label(label="Keybindings")
        add_class(label, "page-heading")
        self.add(label)

        grid = self.build_grid([servers, navigation, vim])
        self.add(grid)

    def build_keys(self, items: list) -> Gtk.Grid:
        grid = Gtk.Grid(row_spacing=10, column_homogeneous=True)
        grid.set_halign(Gtk.Align.START)
        row = 1
        col = 0
        w = 1
        h = 1
        sep = None
        for item in items:
            for k, v in item.items():
                desc = Gtk.Label(label=k)
                desc.set_halign(Gtk.Align.START)

                key = Gtk.Label(label=v)
                key.set_halign(Gtk.Align.CENTER)

                frame = Gtk.Frame()
                frame.add(key)
                add_class(frame, "frame")

                col = col + 1
                if col > 1:
                    row += 1
                    col = 1
                if not sep:
                    grid.attach(desc, col, row, w, h)
                else:
                    grid.attach_next_to(
                        desc, sep, Gtk.PositionType.BOTTOM, w, h
                    )
                    row += 1
                    sep = None
                grid.attach_next_to(frame, desc, Gtk.PositionType.RIGHT, w, h)

            l_spacer = Gtk.Label(label="")
            r_spacer = Gtk.Label(label="")
            grid.attach(l_spacer, col, row + 1, w, h)
            grid.attach_next_to(
                r_spacer, l_spacer, Gtk.PositionType.RIGHT, w, h
            )
            row += 1
        return grid

    def build_sidebar(self, categories: list) -> Gtk.Grid:
        row = 0
        col = 0
        w = 1
        h = 1
        sidebar = Gtk.Grid(
            row_homogeneous=True, orientation=Gtk.Orientation.VERTICAL
        )
        for cat in categories:
            label = Gtk.Label(label=cat)
            add_class(label, "left-label")
            row += 1
            sidebar.attach(label, col, row, w, h)
        return sidebar

    def build_grid(self, items: list) -> Gtk.Grid:
        grid = Gtk.Grid(
            row_spacing=20,
            halign=Gtk.Align.CENTER,
            margin_top=20,
            column_spacing=50,
        )

        row = 1
        column = 1
        w = 1
        h = 1
        sidebar = self.build_sidebar(
            ["Servers", "Navigation", "Vim-style keys"]
        )
        separator = Gtk.Separator()
        keys_box = self.build_keys(items)

        grid.attach(sidebar, column, row, w, h)
        grid.attach_next_to(separator, sidebar, Gtk.PositionType.RIGHT, w, h)
        grid.attach_next_to(keys_box, separator, Gtk.PositionType.RIGHT, w, h)
        return grid


class Changelog(Gtk.Box):
    def __init__(self):
        super().__init__()
        try:
            with open(changelog_path, "r") as f:
                changelog = f.read()
            changelog_label = Gtk.Label()
            changelog = self.format_pango(changelog)
            changelog_label.set_markup(changelog)
            self.add(changelog_label)
        except FileNotFoundError:
            msg = f"Failed to find CHANGELOG.md at {changelog_path}"
            logger.critical(msg)
            spawn_dialog(msg, Popup.WARN)
            return
        except OSError as e:
            spawn_dialog(f"Something went wrong: {e}", Popup.WARN)
            logger.critical(e)
            return

    def format_pango(self, text: str) -> str:
        medium = '<span size="medium"><b>'
        large = '<span size="large"><b>'
        xlarge = '<span size="x-large"><b>'
        text = re.sub("^# ", xlarge, text, flags=re.M)
        text = re.sub("^## ", large, text, flags=re.M)
        text = re.sub("^### ", medium, text, flags=re.M)
        text = re.sub(r"(<span size=.*)", r"\1</b></span>", text)
        return text


class Notebook(Gtk.Notebook):
    def __init__(self):
        super().__init__(show_tabs=False, show_border=False)

        self.clog = ScrollableNote(Changelog())
        self.clog.type = RowType.CHANGELOG
        self.clog.show_all()
        self.append_page(self.clog)
        self.prior_page: int

        self.keys = ScrollableNote(KeybindingsDialog())
        self.keys.type = RowType.KEYBINDINGS
        self.keys.show_all()
        self.append_page(self.keys)

        self.settings = Options()
        self.settings.type = RowType.OPTIONS
        self.settings.show_all()
        self.append_page(self.settings)

        self.connect("switch-page", self._on_page_changed)
        self.connect("key-press-event", self._on_keypress)

    def _set_adjustment(self, adjustment: VAdjustment) -> None:
        INCREMENT = 50
        page = self.get_page()
        if not page:
            return
        allowed_contexts = [RowType.CHANGELOG, RowType.KEYBINDINGS]
        if page.type not in allowed_contexts:
            return
        vadj = page.scrollable.get_vadjustment()
        match adjustment:
            case VAdjustment.TOP:
                adj = vadj.get_lower()
            case VAdjustment.BOTTOM:
                adj = vadj.get_upper()
            case VAdjustment.UP:
                adj = vadj.get_value() - INCREMENT
            case VAdjustment.DOWN:
                adj = vadj.get_value() + INCREMENT
        vadj.set_value(adj)

    def _on_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        match event.keyval:
            case Gdk.KEY_Return:
                page = self.get_page()
                if page:
                    page.back_button.clicked()
            case Gdk.KEY_Right | Gdk.KEY_l:
                if event.state is Gdk.ModifierType.CONTROL_MASK:
                    return
                App.right_panel.focus_button_box()
            case Gdk.KEY_question:
                self.toggle_keybindings()
            case Gdk.KEY_k | Gdk.KEY_Up:
                self._set_adjustment(VAdjustment.UP)
            case Gdk.KEY_Down | Gdk.KEY_j:
                self._set_adjustment(VAdjustment.DOWN)
            case Gdk.KEY_g:
                self._set_adjustment(VAdjustment.TOP)
            case Gdk.KEY_G:
                self._set_adjustment(VAdjustment.BOTTOM)

    def return_prior(self) -> None:
        page = self.get_nth_page(self.prior_page)
        if hasattr(page, "steam_entry"):
            """
            Gtk.Notebook focuses the first input field when changing pages;
            this workaround unhighlights the selected region and makes entry
            fields unfocusable prior to the page 'switch-page' signal,
            then makes them focusable again
            """
            entries = page.steam_entry, page.bm_entry
            for entry in entries:
                entry.set_position(-1)
                entry.set_can_focus(False)
            self.set_current_page(self.prior_page)
            for entry in entries:
                entry.set_can_focus(True)
        self.set_current_page(self.prior_page)

    def toggle_keybindings(self) -> None:
        if self.get_current_page() == NotebookPage.KEYS.value:
            self.return_prior()
        else:
            self.prior_page = self.get_current_page()
            self.set_page_by_enum(NotebookPage.KEYS)

    def focus_current(self) -> None:
        widget = self.get_page()
        if widget:
            w = widget.get_children()[0]
            w.grab_focus()

    def get_page(self) -> Gtk.Widget | None:
        ind = self.get_current_page()
        widget = self.get_nth_page(ind)
        if not widget:
            return None
        return widget

    def set_page_by_enum(self, enum: NotebookPage) -> None:
        self.prior_page = self.get_current_page()
        self.set_current_page(enum.value)
        self.focus_current()
        self._set_adjustment(VAdjustment.TOP)

    @update_window_labels
    def _on_page_changed(
        self, notebook: "Notebook", page: Gtk.Widget, page_num: int
    ) -> None:
        App.treeview.subpage = page.type


class Statusbar(Gtk.Statusbar):
    def __init__(self):
        super().__init__()

        help_text = "Select a row to see its detailed description"
        self.set_text(help_text)
        self.status_right_label = Gtk.Label(label="")
        self.add(self.status_right_label)
        self.update_app_meta()

        self.players = ""

    def get_text(self) -> str:
        area = self.get_message_area()
        label = area.get_children()[0]
        return label.get_text()

    def set_text(self, string: str) -> None:
        if string is None:
            return
        meta = self.get_context_id("Statusbar")
        self.push(meta, string)

    def refresh(self) -> None:
        unsupported_contexts = [
            RowType.KEYBINDINGS,
            RowType.SHOW_LOG,
            RowType.CHANGELOG,
            RowType.OPTIONS,
        ]
        if App.treeview.subpage in unsupported_contexts:
            self.set_text("")
            return
        command = App.treeview.get_value_at_index(0)
        formatted = format_metadata(command)
        if len(formatted) > 0:
            self.set_text(formatted)

    def append_distance(self, dist: str) -> None:
        if dist == "Unknown":
            dist = f"| Distance: {dist}"
        else:
            d = int(dist)
            dist = f"| Distance: {d:n} km"
        self.set_text(self.players + dist)

    def update_server_meta(self) -> None:
        model = App.treeview.get_model()
        if model is None:
            players = 0
            hits = 0
        else:
            hits = len(model)
            players = 0
            for row in model:
                players += row[4]

        players_pretty = pluralize("players", players)
        hits_pretty = pluralize("matches", hits)
        formatted = (
            f"Found {hits:n} {hits_pretty} with {players:n} {players_pretty}"
        )
        suffix = "| Distance: calculating..."

        if players == 0:
            suffix = ""
        self.set_text(formatted + suffix)
        self.players = formatted

    def update_app_meta(self) -> None:
        config_vals.clear()
        for i in query_config():
            config_vals.append(i)
        concat_label = f"{_VERSION}"
        self.status_right_label.set_text(concat_label)


class Grid(Gtk.Grid):
    def __init__(self):
        super().__init__()
        self.set_column_homogeneous(True)

        self._version = f"{app_name} {_VERSION}"

        self.scrollable_treelist = ScrollableTree()
        self.scrollable_treelist.set_hexpand(False)
        self.scrollable_treelist.set_vexpand(True)
        self.scrollable_treelist.treeview.connect(
            "on_distcalc_started", self._on_calclat_started
        )

        self.right_panel = RightPanel()
        self.sel_panel = ModSelectionPanel()
        self.right_panel.pack_start(self.sel_panel, False, False, 0)

        """
        Note that due to historical reasons, Gtk.Notebook refuses to
        switch to a page unless the child widget is visible.
        Therefore, it is recommended to show child widgets
        before adding them to a notebook.

        """
        self.show_all()
        self.scrollable_treelist.type = None
        self.notebook = Notebook()
        self.notebook.insert_page(self.scrollable_treelist, None, 0)

        self.statusbar = Statusbar()
        GLib.timeout_add(200, self._check_result_queue)

        self.breadcrumbs = Gtk.Label(label="Main menu", halign=Gtk.Align.START)

        self.attach(self.notebook, 0, 0, 3, 1)
        self.attach_next_to(
            self.breadcrumbs, self.notebook, Gtk.PositionType.TOP, 3, 1
        )
        self.attach_next_to(
            self.statusbar, self.notebook, Gtk.PositionType.BOTTOM, 3, 1
        )
        self.attach_next_to(
            self.right_panel, self.notebook, Gtk.PositionType.RIGHT, 1, 1
        )

    def get_breadcrumbs(self) -> str:
        return self.breadcrumbs.get_text()

    def set_breadcrumbs(self, text: str) -> None:
        self.breadcrumbs.set_text(text)

    def terminate_treeview_process(self) -> None:
        self.scrollable_treelist.treeview.terminate_process()

    def _on_calclat_started(self, treeview: Gtk.TreeView) -> None:
        App.grid.statusbar.update_server_meta()

    def _check_result_queue(self) -> Literal[True]:
        latest_result = None
        result_queue = self.scrollable_treelist.treeview.queue
        while not result_queue.empty():
            latest_result = result_queue.get()

        if latest_result:
            addr = latest_result[0]
            km = latest_result[1]
            cache[addr] = km
            self.statusbar.append_distance(km)
        return True


class App(Gtk.Application):
    def __init__(self):
        _isd = int(sys.argv[3])
        global IS_STEAM_DECK
        global IS_GAME_MODE
        if _isd == 1:
            IS_STEAM_DECK = True
            IS_GAME_MODE = False
        elif _isd == 2:
            IS_STEAM_DECK = True
            IS_GAME_MODE = True
        else:
            IS_STEAM_DECK = False
            IS_GAME_MODE = False

        GLib.set_prgname(app_name)
        self.win = OuterWindow()
        self.win.set_icon_name("{app_name_lower}")

        accel = Gtk.AccelGroup()
        accel.connect(
            Gdk.KEY_q,
            Gdk.ModifierType.CONTROL_MASK,
            Gtk.AccelFlags.VISIBLE,
            self._halt_window_subprocess,
        )
        self.win.add_accel_group(accel)

        GLib.unix_signal_add(
            GLib.PRIORITY_DEFAULT, signal.SIGINT, self._catch_sigint
        )
        Gtk.main()

    def _catch_sigint(self) -> None:
        self.win.halt_proc_and_quit()

    def _halt_window_subprocess(
        self,
        accel_group: Gtk.AccelGroup,
        window: "OuterWindow",
        code: Gdk.EventKey,
        flag: Gdk.ModifierType,
    ) -> None:
        self.win.halt_proc_and_quit()


class ModSelectionPanel(Gtk.Box):
    def __init__(self):
        super().__init__(spacing=6)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        labels = [
            {"label": "Select all", "tooltip": "Bulk selects all mods"},
            {"label": "Unselect all", "tooltip": "Bulk unselects all mods"},
            {
                "label": "Delete selected",
                "tooltip": "Deletes selected mods from the system",
            },
            {
                "label": "Highlight stale",
                "tooltip": "Shows locally-installed mods which are not\n"
                "used by any server in your Saved Servers",
            },
        ]

        self.active_button = None

        for label in labels:
            button = Gtk.Button(label=label["label"])
            button.set_tooltip_text(label["tooltip"])
            button.set_margin_start(10)
            button.set_margin_end(10)
            button.connect("clicked", self._on_button_clicked)
            self.pack_start(button, False, True, 0)

    def initialize(self) -> None:
        for i in self.get_children():
            match i.get_label():
                case "Select stale":
                    i.destroy()
                case "Unhighlight stale":
                    i.set_label("Highlight stale")

    def _on_button_clicked(self, button: Gtk.Button) -> None:
        self.active_button = button
        label = button.get_label()
        treeview = App.treeview
        (model, pathlist) = treeview.get_selection().get_selected_rows()
        match label:
            case "Select all":
                treeview.toggle_selection(True)
            case "Unselect all":
                treeview.toggle_selection(False)
            case "Delete selected":
                ct = len(pathlist)
                if ct < 1:
                    return
                self._iterate_mod_deletion(model, pathlist, ct)
            case "Highlight stale":
                process_tree_option(RowType.HIGHLIGHT)
            case "Unhighlight stale":
                self.colorize_cells(False)
                self._remove_last_button()
            case "Select stale":
                for i in range(0, len(mod_store)):
                    if mod_store[i][4] == "#FF0000":
                        path = Gtk.TreePath.new_from_indices([i])
                        treeview.get_selection().select_path(path)

    def _remove_last_button(self) -> None:
        children = self.get_children()
        tip = children[-1]
        label = tip.get_label()
        if label == "Select stale":
            tip.destroy()

    def toggle_select_stale_button(self, state: bool) -> None:
        if state:
            button = Gtk.Button(
                label="Select stale", margin_start=10, margin_end=10
            )
            text = "Bulk selects all currently highlighted mods"
            button.set_tooltip_text(text)
            button.connect("clicked", self._on_button_clicked)
            self.pack_start(button, False, True, 0)
            self.show_all()

    def colorize_cells(self, state: bool) -> None:
        def _colorize(path, color):
            mod_store[path][4] = color

        treeview = App.treeview
        (model, pathlist) = treeview.get_selection().get_selected_rows()

        if not state:
            for i in range(0, len(mod_store)):
                path = Gtk.TreePath.new_from_indices([i])
                it = mod_store.get_iter(path)
                _colorize(path, None)
            self.active_button.set_label("Highlight stale")
            return

        with open(stale_mods_temp_file, "r") as infile:
            lines = [line.rstrip("\n") for line in infile]

        hits = 0
        for i, row in enumerate(mod_store):  # type: ignore
            red = "#FF0000"
            path = Gtk.TreePath.new_from_indices([i])
            it = mod_store.get_iter(path)
            if model.get_value(it, 2) not in lines:
                hits += 1
                _colorize(path, red)
            treeview.toggle_selection(False)
        if hits > 0:
            self.active_button.set_label("Unhighlight stale")
            text = "Clears highlights and reverts the table to a default state"
            self.active_button.set_tooltip_text(text)
            self.toggle_select_stale_button(True)

    def _iterate_mod_deletion(
        self, model: Gtk.ListStore, pathlist: list, ct: int
    ) -> None:
        pretty = pluralize("mods", ct)
        conf_msg = f"You are going to delete {ct} {pretty}. Proceed?"
        res = spawn_dialog(conf_msg, Popup.CONFIRM)
        if res != 0:
            return

        mods = []
        for i in pathlist:
            it = model.get_iter(i)
            symlink = model.get_value(it, 1)
            path = model.get_value(it, 2)
            concat = symlink + " " + path + "\n"
            mods.append(concat)
        # use a temp file to avoid passing too many args to shell
        with open(mods_temp_file, "w") as outfile:
            outfile.writelines(mods)
        process_tree_option(RowType.DELETE_SELECTED)


class FilterPanel(Gtk.Box):
    def __init__(self):
        super().__init__(spacing=6)

        self.default_filters = {
            "1PP": True,
            "Day": True,
            "Empty": False,
            "3PP": True,
            "Night": True,
            "Full": False,
            "Low pop": True,
            "Non-ASCII": False,
            "Duplicate": False,
            "Official": True,
            "Unoffic.": True,
            "Modded": True,
        }

        self.checks = []
        self.maps_hr = []
        self.enabled_filters = dict(self.default_filters)
        self.keyword_filter = ""
        self.selected_map = "All maps"
        self.prior_map = "All maps"

        button_grid = Gtk.Grid(
            halign=Gtk.Align.CENTER, column_spacing=5, column_homogeneous=True
        )
        row = 1
        col = 0
        for check in self.default_filters.keys():
            checkbox = Gtk.CheckButton(label=check)
            label = checkbox.get_children()
            label[0].set_ellipsize(Pango.EllipsizeMode.END)

            if self.default_filters[check]:
                checkbox.set_active(True)

            col = col + 1
            if col > 3:
                row += 1
                col = 1
            button_grid.attach(checkbox, col, row, 1, 1)

            checkbox.connect("toggled", self._on_check_toggled)
            self.checks.append(checkbox)

        self.connect("button-release-event", self._on_button_release)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        set_surrounding_margins(self, 10)
        self.set_margin_top(1)

        self.filters_label = Gtk.Label(label="Filters")

        self.keyword_entry = Gtk.Entry()
        self.keyword_entry.set_placeholder_text("Filter by keyword")
        self.keyword_entry.connect("activate", self._on_keyword_enter)
        self.keyword_entry.connect(
            "key-press-event", self._on_keyword_keypress
        )

        completion = Gtk.EntryCompletion(inline_completion=True)
        completion.set_text_column(0)
        completion.set_minimum_key_length(1)
        completion.connect("match_selected", self._on_completer_match)

        renderer_text = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
        self.maps_combo = Gtk.ComboBox.new_with_model_and_entry(map_store)
        self.maps_combo.set_entry_text_column(0)

        self.maps_entry = self.maps_combo.get_child()
        self.maps_entry.set_completion(completion)
        self.maps_entry.set_placeholder_text("Filter by map")
        self.maps_entry.connect("changed", self._on_map_completion, True)
        self.maps_entry.connect("key-press-event", self._on_map_entry_keypress)

        self.maps_combo.pack_start(renderer_text, True)
        self.maps_combo.connect("changed", self._on_map_changed)
        self.maps_combo.connect("key-press-event", self._on_combo_keypress)

        self.pack_start(self.filters_label, False, False, 0)
        self.pack_start(self.keyword_entry, False, False, 0)
        self.pack_start(self.maps_combo, False, False, 0)

        self.pack_start(button_grid, False, False, 0)

    def set_unique_maps(self, maps: list) -> None:
        if len(maps) < 1:
            return
        u_maps = set([row[1] for row in maps])  # type: ignore
        u_maps = sorted(u_maps)  # type: ignore
        for m in u_maps:
            map_store.append([m])
            self.maps_hr.append(m)

    def get_filters(self) -> tuple:
        filters = []
        filters.append(self.selected_map)
        filters.append(self.keyword_filter)
        for k in self.enabled_filters:
            if not self.enabled_filters[k]:
                filters.append(k)
        return tuple(filters)

    # used on personal/local server lists
    def enable_all_filters(self) -> None:
        for check in self.checks:
            check.set_active(True)
        for k in self.enabled_filters:
            self.enabled_filters[k] = True

    def reinit_panel(self) -> None:
        self.keyword_entry.set_text("")
        self.keyword_filter = ""
        self.reinit_filters()
        self.set_visible(False)
        sel_panel = App.grid.sel_panel
        if sel_panel.is_visible():
            sel_panel.set_visible(False)

    def reinit_filters(self) -> None:
        self.enabled_filters = dict(self.default_filters)
        for check in self.checks:
            label = check.get_label()
            state = self.default_filters[label]
            check.set_active(state)

    def _on_map_entry_keypress(
        self, entry: Gtk.Entry, event: Gdk.EventKey
    ) -> None:
        match event.keyval:
            case Gdk.KEY_Return:
                text = entry.get_text()
                if text is None:
                    return
                """
                If entry is exact match for value in liststore,
                trigger map change function
                """
                for i in enumerate(map_store):  # type: ignore
                    if text == i[1][0]:
                        self.maps_combo.set_active(i[0])
                        self._on_map_changed(self.maps_combo)
            case Gdk.KEY_Escape:
                GLib.idle_add(self.restore_focus_to_treeview)
                """
                This is a workaround for widget.grab_remove()
                Sets cursor position to SOL when unfocusing
                """
                text = self.maps_entry.get_text()
                self.maps_entry.set_position(len(text))
            case _:
                return

    def _on_completer_match(
        self,
        completion: Gtk.EntryCompletion,
        model: Gtk.ListStore,
        it: Gtk.TreeIter,
    ) -> None:
        self.maps_combo.set_active_iter(it)

    def _on_map_completion(self, entry, editable):
        text = entry.get_text()
        completion = entry.get_completion()
        if len(text) >= completion.get_minimum_key_length():
            completion.set_model(map_store)

    def restore_focus_to_treeview(self) -> Literal[False]:
        App.treeview.grab_focus()
        return False

    def _on_keyword_keypress(
        self, entry: Gtk.Entry, event: Gdk.EventKey
    ) -> bool:
        match event.keyval:
            case Gdk.KEY_Up:
                return True
            case Gdk.KEY_Down:
                return True
            case Gdk.KEY_Escape:
                GLib.idle_add(self.restore_focus_to_treeview)
                return True
        return False

    def _on_combo_keypress(
        self, combo: Gtk.ComboBox, event: Gdk.EventKey
    ) -> bool:
        match event.keyval:
            case Gdk.KEY_Down:
                self.maps_combo.popup()
                return True
            case _:
                return False

    def set_prior_map(self, mapname: str) -> None:
        self.prior_map = mapname

    def get_prior_map(self) -> str:
        return self.prior_map

    def get_selected_map(self) -> str:
        return self.selected_map

    def get_keyword_filter(self) -> str:
        return self.keyword_filter

    def _on_keyword_enter(self, entry: Gtk.Entry) -> None:
        App.window.set_keep_below(False)
        keyword = entry.get_text().lower()
        if keyword == self.keyword_filter:
            return
        if keyword.isspace():
            return
        logger.info(f"User filtered by keyword '{keyword}'")
        self.keyword_filter = keyword
        App.treeview.filter(FilterMode.KEYWORD, keyword)

    def _on_button_release(self, window, button) -> Literal[True]:
        return True

    def get_active_combo(self) -> int:
        return self.maps_combo.get_active()

    def set_active_combo(self, row: int) -> None:
        self.maps_combo.set_active(row)

    def toggle_check(self, digit: int) -> None:
        check = self.checks[digit]
        state = check.get_active()
        check.set_active(not state)

    def _on_check_toggled(self, button: Gtk.CheckButton) -> None:
        if not App.treeview.is_server_context(App.treeview.view):
            return
        label = button.get_label()
        state = button.get_active()
        logger.info(f"User toggled button '{label}' to {state}")
        if state:
            mode = FilterMode.TOGGLE_ON
        else:
            mode = FilterMode.TOGGLE_OFF

        self.enabled_filters[label] = state
        App.treeview.filter(mode, label)

    def _on_map_changed(self, combo: Gtk.ComboBox) -> None:
        old_sel = self.selected_map
        model = combo.get_model()
        tree_iter = combo.get_active_iter()
        if tree_iter is None:
            return
        selection = model[tree_iter][0]
        if selection == old_sel:
            return
        if not selection:
            return
        logger.info(f"User selected map '{selection}'")
        self.prior_map = self.selected_map
        self.selected_map = selection
        self.maps_entry.set_text(selection)
        App.treeview.filter(FilterMode.MAP)


def main():
    def usage():
        text = "UI helper must be run via DZGUI"
        logger.critical(text)
        print(text)
        sys.exit(1)

    expected_flag = "--init-ui"
    if len(sys.argv) < 2:
        usage()
    if sys.argv[1] != expected_flag:
        usage()

    logger.info("Spawned UI from DZGUI setup process")
    global _VERSION
    _VERSION = sys.argv[2]
    App()


ModelManager = ModelManagerSingleton()
if __name__ == "__main__":
    main()
