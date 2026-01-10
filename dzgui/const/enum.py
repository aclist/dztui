from enum import Enum
from typing import Self

from dzgui.util import strings


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


class Command(Enum):
    INTERACTIVE = 1
    ONESHOT = 2
    HELP = 3
    TOGGLE = 4
    THANKS = 5


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

class Preferences(EnumWithAttrs):
    STEAM = {"key": "steam_api",}
    BM = {"key": "bm_api",}
    CLIENT = {"key": "client",}
    WINDOW = {"key": "fullscreen",}
    DIST = {"key": "use_miles",}
    NAME = {"key": "name",}
    INSTALL = {"key": "auto_install",}
    DEBUG = {"key": "debug",}
    DEFAULT = {"key": "default_steam_path",}
    FAV_LBL = {"key": "fav_label",}
    FAV_SRV = {"key": "fav_server",}
    IP_LIST = {"key": "ip_list",}
    BRANCH = {"key": "branch",}


class NotebookPage(EnumWithAttrs):
    CHANGELOG = {"crumbs": strings.crumbs.changelog, "statusbar": False}
    KEYS = {"crumbs": strings.crumbs.keys, "statusbar": False}
    LOG = {"crumbs": strings.crumbs.log, "statusbar": False}
    HELP = {"crumbs": strings.crumbs._help, "statusbar": True}
    MODS = {"crumbs": strings.crumbs.mods, "statusbar": True}
    OPTIONS = {"crumbs": strings.crumbs.options, "statusbar": False}
    SERVERS = {"crumbs": strings.crumbs.servers, "statusbar": True}
    THANKS = {"crumbs": strings.crumbs.thanks, "statusbar": False}
    DEVELOPERS = {"crumbs": strings.crumbs.developers, "statusbar": False}


class RowType(EnumWithAttrs):
    @classmethod
    def str2rowtype(cls, string: str) -> "RowType":
        for member in cls:
            if string == member.dict["label"]:
                return member
        return RowType.DYNAMIC

    # specialized behavior
    # TODO: deprecated
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
        "label": "Mods",
        "tooltip": "Browse a list of locally-installed mods",
        "quad_label": "Mods",
        "type": "mods",
    }
    CHANGELOG = {
        "label": "View changelog",
        "tooltip": "Opens the DZGUI changelog",
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
    SEPARATOR = {
        "label" : "SEPARATOR",
        "tooltip": "",
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
        "tooltip": "Open the DZGUI documentation in a browser",
        "type": Command.HELP,
    }
    DOCS_FALLBACK = {
        "label": "Documentation/help files (Codeberg mirror) ⧉",
        "tooltip": "Open the DZGUI documentation in a browser",
        "type": Command.HELP,
    }
    BUGS = {
        "label": "Report a bug (GitHub) ⧉",
        "tooltip": "Open the DZGUI issue tracker in a browser",
        "type": Command.HELP,
    }
    FORUM = {
        "label": "DZGUI Subreddit ⧉",
        "tooltip": "Open the DZGUI discussion forum in a browser",
        "type": Command.HELP,
    }
    SPONSOR = {
        "label": "Sponsor (GitHub) ⧉",
        "tooltip": "Sponsor development of the DZGUI project",
        "type": Command.HELP,
    }
    THANKS = {
        "label": "Special thanks",
        "tooltip": "A list of contributors, testers, and sponsors",
        "type": Command.THANKS,
    }


# TODO: rename to ContextItem
class ContextMenu(EnumWithAttrs):
    ADD_SERVER = {"label": strings.add}
    ADD_FAV = {"label": strings.add_fav}
    REMOVE_SERVER = {"label": strings.remove}
    COPY_NAME = {"label": strings.copy_name}
    COPY_CLIPBOARD = {"label": strings.copy_ip}
    ADD_NOTE = {"label": strings.add_note}
    SHOW_MODS = {"label": strings.show_mods}
    SHOW_DETAILS = {"label": strings.show_details}
    REFRESH_PLAYERS = {"label": strings.refresh_players}
    REMOVE_HISTORY = {"label": strings.remove_history}
    OPEN_WORKSHOP = {"label": strings.open_workshop}
    DELETE_MOD = {"label": strings.delete_mod}
    COPY_LOG_CLIPBOARD = {"label": strings.copy_log}
    CONNECT = {"label": strings.connect}


class ContextMenuGroup(Enum):
    """
    Groupings of context menu items
    """
    MOD = (
        ContextMenu.OPEN_WORKSHOP, ContextMenu.DELETE_MOD
    )
    LOG = (
        ContextMenu.COPY_LOG_CLIPBOARD,
    )
    SERVER_BROWSER = (
        ContextMenu.CONNECT,
        ContextMenu.ADD_SERVER,
        ContextMenu.ADD_FAV,
        ContextMenu.COPY_NAME,
        ContextMenu.COPY_CLIPBOARD,
        ContextMenu.ADD_NOTE,
        ContextMenu.SHOW_MODS,
        ContextMenu.SHOW_DETAILS,
        ContextMenu.REFRESH_PLAYERS,
    )
    SCAN_LAN = (
        ContextMenu.CONNECT,
        ContextMenu.ADD_FAV,
        ContextMenu.COPY_NAME,
        ContextMenu.COPY_CLIPBOARD,
        ContextMenu.ADD_NOTE,
        ContextMenu.SHOW_MODS,
        ContextMenu.SHOW_DETAILS,
        ContextMenu.REFRESH_PLAYERS,
    )
    SAVED = (
        ContextMenu.CONNECT,
        ContextMenu.ADD_FAV,
        ContextMenu.REMOVE_SERVER,
        ContextMenu.COPY_NAME,
        ContextMenu.COPY_CLIPBOARD,
        ContextMenu.ADD_NOTE,
        ContextMenu.SHOW_MODS,
        ContextMenu.SHOW_DETAILS,
        ContextMenu.REFRESH_PLAYERS,
    )
    RECENT = (
        ContextMenu.CONNECT,
        ContextMenu.ADD_SERVER,
        ContextMenu.ADD_FAV,
        ContextMenu.REMOVE_HISTORY,
        ContextMenu.COPY_NAME,
        ContextMenu.COPY_CLIPBOARD,
        ContextMenu.ADD_NOTE,
        ContextMenu.SHOW_MODS,
        ContextMenu.SHOW_DETAILS,
        ContextMenu.REFRESH_PLAYERS,
    )

class ModButton(EnumWithAttrs):
    SELECT_ALL = {
        "label": strings.mod_panel.select_all,
        "tooltip": strings.mod_panel.select_all_tooltip,
    }
    UNSELECT_ALL = {
        "label": strings.mod_panel.unselect_all,
        "tooltip": strings.mod_panel.unselect_all_tooltip
    }
    HIGHLIGHT_STALE = {
        "label": strings.mod_panel.highlight_stale,
        "tooltip": strings.mod_panel.highlight_stale_tooltip,
    }
    UNHIGHLIGHT_STALE = {
        "label": strings.mod_panel.unhighlight_stale,
        "tooltip": strings.mod_panel.unhighlight_stale_tooltip,
    }
    DELETE_SELECTED = {
        "label": strings.mod_panel.delete_selected,
        "tooltip": strings.mod_panel.delete_selected_tooltip,
    }
    SELECT_STALE = {
       "label": strings.mod_panel.select_stale,
       "tooltip": strings.mod_panel.select_stale_tooltip,
    }


class ButtonType(EnumWithAttrs):
    SERVERS = {
        "label": strings.buttons.servers_label,
        "tooltip": strings.buttons.servers_tooltip,
        "opens": NotebookPage.SERVERS,
    }
    MODS = {
        "label": strings.buttons.mods_label,
        "tooltip": strings.buttons.mods_tooltip,
        "opens": NotebookPage.MODS,
    }
    OPTIONS = {
        "label": strings.buttons.options_label,
        "tooltip": strings.buttons.options_tooltip,
        "opens": NotebookPage.OPTIONS
   }
    HELP = {
        "label": strings.buttons.help_label,
        "tooltip": strings.buttons.help_tooltip,
        "opens": NotebookPage.HELP,
    }
    EXIT = {
        "label": strings.buttons.exit_label,
        "tooltip": strings.buttons.exit_tooltip,
        "opens": None,
    }


HELP_MENU_ROWS = (
    RowType.CHANGELOG,
    RowType.SHOW_LOG,
    RowType.DUMP_LOG,
    RowType.SEPARATOR,
    RowType.DOCS,
    RowType.DOCS_FALLBACK,
    RowType.BUGS,
    RowType.FORUM,
    RowType.SPONSOR,
    RowType.SEPARATOR,
    RowType.THANKS,
)

class ServerTab(Enum):
    BROWSER = 1
    SAVED = 2
    RECENT = 3
    LAN = 4
